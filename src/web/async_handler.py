"""
비동기 처리 핸들러 모듈

이 모듈은 Flask-SocketIO를 사용한 비동기 파일 처리와
실시간 진행률 업데이트를 담당합니다.
"""

import asyncio
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from flask_socketio import SocketIO

from ..core.multi_file_handler import MultiFileHandler
from ..models.models import ConversionResult
from ..models.processing_options import ProcessingOptions, ProgressInfo


class AsyncProcessingHandler:
    """
    비동기 처리를 위한 핸들러 클래스

    Flask-SocketIO와 MultiFileHandler를 연결하여
    실시간 진행률 업데이트와 백그라운드 처리를 제공합니다.
    """

    def __init__(self, socketio: SocketIO, multi_file_handler: MultiFileHandler):
        """
        AsyncProcessingHandler 초기화

        Args:
            socketio: Flask-SocketIO 인스턴스
            multi_file_handler: 다중 파일 처리 핸들러
        """
        self.socketio = socketio
        self.multi_file_handler = multi_file_handler

        # 활성 백그라운드 작업 추적
        self.active_tasks: Dict[str, threading.Thread] = {}

        # 작업 취소 플래그
        self.cancellation_flags: Dict[str, threading.Event] = {}

    def start_batch_processing(
        self,
        queue_id: str,
        temp_files: List[str],
        processing_options: ProcessingOptions,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
    ) -> bool:
        """
        배치 처리를 백그라운드에서 시작

        Args:
            queue_id: 큐 식별자
            temp_files: 임시 파일 경로 목록
            processing_options: 처리 옵션
            processor_func: 파일 처리 함수

        Returns:
            처리 시작 성공 여부
        """
        try:
            # 취소 플래그 생성
            cancellation_flag = threading.Event()
            self.cancellation_flags[queue_id] = cancellation_flag

            # 백그라운드 처리 함수
            def background_processor():
                self._process_queue_background(
                    queue_id,
                    temp_files,
                    processing_options,
                    processor_func,
                    cancellation_flag,
                )

            # 백그라운드 스레드 시작
            thread = threading.Thread(target=background_processor, daemon=True)
            thread.start()

            self.active_tasks[queue_id] = thread

            return True

        except Exception as e:
            print(f"Error starting batch processing: {e}")
            return False

    def cancel_batch_processing(self, queue_id: str) -> bool:
        """
        배치 처리 취소

        Args:
            queue_id: 큐 식별자

        Returns:
            취소 성공 여부
        """
        try:
            # MultiFileHandler에서 취소
            success = self.multi_file_handler.cancel_processing(queue_id)

            if success:
                # 취소 플래그 설정
                if queue_id in self.cancellation_flags:
                    self.cancellation_flags[queue_id].set()

                # WebSocket으로 취소 알림
                self.socketio.emit(
                    "batch_cancelled",
                    {
                        "queue_id": queue_id,
                        "message": "배치 처리가 취소되었습니다.",
                        "timestamp": time.time(),
                    },
                    room=f"queue_{queue_id}",
                )

                # 작업 정리
                self._cleanup_task(queue_id)

            return success

        except Exception as e:
            print(f"Error cancelling batch processing: {e}")
            return False

    def get_active_tasks(self) -> List[str]:
        """
        활성 작업 목록 반환

        Returns:
            활성 큐 ID 목록
        """
        return list(self.active_tasks.keys())

    def cleanup_completed_tasks(self) -> int:
        """
        완료된 작업들 정리

        Returns:
            정리된 작업 수
        """
        completed_tasks = []

        for queue_id, thread in self.active_tasks.items():
            if not thread.is_alive():
                completed_tasks.append(queue_id)

        for queue_id in completed_tasks:
            self._cleanup_task(queue_id)

        return len(completed_tasks)

    def _process_queue_background(
        self,
        queue_id: str,
        temp_files: List[str],
        processing_options: ProcessingOptions,
        processor_func: Callable[[str, ProcessingOptions], ConversionResult],
        cancellation_flag: threading.Event,
    ):
        """
        백그라운드에서 큐 처리 실행

        Args:
            queue_id: 큐 식별자
            temp_files: 임시 파일 경로 목록
            processing_options: 처리 옵션
            processor_func: 파일 처리 함수
            cancellation_flag: 취소 플래그
        """
        try:
            # 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 진행률 콜백 함수
            def progress_callback(progress_info: ProgressInfo):
                if not cancellation_flag.is_set():
                    self.socketio.emit(
                        "batch_progress",
                        {
                            "queue_id": progress_info.queue_id,
                            "total_files": progress_info.total_files,
                            "completed_files": progress_info.completed_files,
                            "current_file": progress_info.current_file,
                            "estimated_time_remaining": progress_info.estimated_time_remaining,
                            "status": progress_info.status,
                            "error_count": progress_info.error_count,
                            "progress_percentage": progress_info.progress_percentage,
                            "current_file_progress": progress_info.current_file_progress,
                            "timestamp": time.time(),
                        },
                        room=f"queue_{queue_id}",
                    )

            # 큐에 진행률 콜백 등록
            if queue_id in self.multi_file_handler._queues:
                queue = self.multi_file_handler._queues[queue_id]
                queue.progress_callback = progress_callback

            # 비동기 처리 실행
            async def run_processing():
                results = []
                try:
                    async for result in self.multi_file_handler.process_queue(
                        queue_id, processor_func
                    ):
                        if cancellation_flag.is_set():
                            break

                        results.append(result)

                        # 각 파일 처리 완료 시 WebSocket으로 알림
                        self.socketio.emit(
                            "file_processed",
                            {
                                "queue_id": queue_id,
                                "file_path": result.file_path,
                                "success": result.success,
                                "error_message": (
                                    result.error_message if not result.success else None
                                ),
                                "processing_time": getattr(
                                    result, "processing_time", 0.0
                                ),
                                "file_size": result.file_size if result.success else 0,
                                "format": result.format if result.success else None,
                                "timestamp": time.time(),
                            },
                            room=f"queue_{queue_id}",
                        )

                    # 취소되지 않은 경우에만 완료 알림
                    if not cancellation_flag.is_set():
                        # 처리 요약 정보 가져오기
                        processing_summary = (
                            self.multi_file_handler.get_processing_summary(queue_id)
                        )
                        failed_files = self.multi_file_handler.get_failed_files(
                            queue_id
                        )

                        self.socketio.emit(
                            "batch_completed",
                            {
                                "queue_id": queue_id,
                                "total_files": len(results),
                                "successful_files": sum(
                                    1 for r in results if r.success
                                ),
                                "failed_files": sum(
                                    1 for r in results if not r.success
                                ),
                                "processing_summary": processing_summary,
                                "failed_file_details": failed_files,
                                "timestamp": time.time(),
                            },
                            room=f"queue_{queue_id}",
                        )

                except asyncio.CancelledError:
                    self.socketio.emit(
                        "batch_cancelled",
                        {
                            "queue_id": queue_id,
                            "message": "배치 처리가 취소되었습니다.",
                            "timestamp": time.time(),
                        },
                        room=f"queue_{queue_id}",
                    )
                except Exception as e:
                    self.socketio.emit(
                        "batch_error",
                        {
                            "queue_id": queue_id,
                            "error": str(e),
                            "timestamp": time.time(),
                        },
                        room=f"queue_{queue_id}",
                    )

                return results

            # 처리 실행
            loop.run_until_complete(run_processing())

        except Exception as e:
            print(f"Background processing error: {e}")
            self.socketio.emit(
                "batch_error",
                {"queue_id": queue_id, "error": str(e), "timestamp": time.time()},
                room=f"queue_{queue_id}",
            )
        finally:
            # 임시 파일들 정리
            for temp_file in temp_files:
                try:
                    import os

                    os.unlink(temp_file)
                except:
                    pass

            # 작업 정리
            self._cleanup_task(queue_id)

            # 이벤트 루프 정리
            try:
                loop.close()
            except:
                pass

    def _cleanup_task(self, queue_id: str):
        """
        작업 정리

        Args:
            queue_id: 큐 식별자
        """
        # 활성 작업에서 제거
        if queue_id in self.active_tasks:
            del self.active_tasks[queue_id]

        # 취소 플래그 제거
        if queue_id in self.cancellation_flags:
            del self.cancellation_flags[queue_id]

    def get_task_status(self, queue_id: str) -> Optional[Dict[str, Any]]:
        """
        작업 상태 정보 반환

        Args:
            queue_id: 큐 식별자

        Returns:
            작업 상태 정보 또는 None
        """
        if queue_id not in self.active_tasks:
            return None

        thread = self.active_tasks[queue_id]
        is_cancelled = (
            queue_id in self.cancellation_flags
            and self.cancellation_flags[queue_id].is_set()
        )

        return {
            "queue_id": queue_id,
            "is_alive": thread.is_alive(),
            "is_cancelled": is_cancelled,
            "thread_name": thread.name,
        }

    def shutdown(self):
        """
        핸들러 종료 및 정리
        """
        # 모든 작업 취소
        for queue_id in list(self.active_tasks.keys()):
            self.cancel_batch_processing(queue_id)

        # 모든 스레드가 종료될 때까지 대기 (최대 5초)
        for thread in self.active_tasks.values():
            thread.join(timeout=5.0)

        # 강제 정리
        self.active_tasks.clear()
        self.cancellation_flags.clear()


class WebSocketProgressTracker:
    """
    WebSocket을 통한 진행률 추적 유틸리티
    """

    def __init__(self, socketio: SocketIO):
        """
        WebSocketProgressTracker 초기화

        Args:
            socketio: Flask-SocketIO 인스턴스
        """
        self.socketio = socketio
        self.tracked_queues: Dict[str, Dict[str, Any]] = {}

    def start_tracking(self, queue_id: str, room_name: Optional[str] = None):
        """
        큐 진행률 추적 시작

        Args:
            queue_id: 큐 식별자
            room_name: WebSocket 룸 이름 (기본값: queue_{queue_id})
        """
        if room_name is None:
            room_name = f"queue_{queue_id}"

        self.tracked_queues[queue_id] = {
            "room_name": room_name,
            "start_time": time.time(),
            "last_update": time.time(),
        }

    def stop_tracking(self, queue_id: str):
        """
        큐 진행률 추적 중지

        Args:
            queue_id: 큐 식별자
        """
        if queue_id in self.tracked_queues:
            del self.tracked_queues[queue_id]

    def emit_progress(self, queue_id: str, progress_data: Dict[str, Any]):
        """
        진행률 정보 전송

        Args:
            queue_id: 큐 식별자
            progress_data: 진행률 데이터
        """
        if queue_id not in self.tracked_queues:
            return

        room_name = self.tracked_queues[queue_id]["room_name"]
        self.tracked_queues[queue_id]["last_update"] = time.time()

        # 타임스탬프 추가
        progress_data["timestamp"] = time.time()

        self.socketio.emit("batch_progress", progress_data, room=room_name)

    def emit_file_completed(self, queue_id: str, file_data: Dict[str, Any]):
        """
        파일 처리 완료 알림

        Args:
            queue_id: 큐 식별자
            file_data: 파일 처리 결과 데이터
        """
        if queue_id not in self.tracked_queues:
            return

        room_name = self.tracked_queues[queue_id]["room_name"]
        file_data["timestamp"] = time.time()

        self.socketio.emit("file_processed", file_data, room=room_name)

    def emit_batch_completed(self, queue_id: str, summary_data: Dict[str, Any]):
        """
        배치 처리 완료 알림

        Args:
            queue_id: 큐 식별자
            summary_data: 처리 요약 데이터
        """
        if queue_id not in self.tracked_queues:
            return

        room_name = self.tracked_queues[queue_id]["room_name"]
        summary_data["timestamp"] = time.time()

        self.socketio.emit("batch_completed", summary_data, room=room_name)

        # 추적 중지
        self.stop_tracking(queue_id)

    def emit_error(self, queue_id: str, error_data: Dict[str, Any]):
        """
        오류 알림

        Args:
            queue_id: 큐 식별자
            error_data: 오류 데이터
        """
        if queue_id not in self.tracked_queues:
            return

        room_name = self.tracked_queues[queue_id]["room_name"]
        error_data["timestamp"] = time.time()

        self.socketio.emit("batch_error", error_data, room=room_name)

        # 추적 중지
        self.stop_tracking(queue_id)

    def get_tracked_queues(self) -> List[str]:
        """
        추적 중인 큐 목록 반환

        Returns:
            큐 ID 목록
        """
        return list(self.tracked_queues.keys())

    def cleanup_stale_tracking(self, max_age_seconds: float = 3600):
        """
        오래된 추적 정보 정리

        Args:
            max_age_seconds: 최대 추적 시간 (초)
        """
        current_time = time.time()
        stale_queues = []

        for queue_id, tracking_info in self.tracked_queues.items():
            if current_time - tracking_info["last_update"] > max_age_seconds:
                stale_queues.append(queue_id)

        for queue_id in stale_queues:
            self.stop_tracking(queue_id)

        return len(stale_queues)
