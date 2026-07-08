"""
JARVIS AI OS - gRPC Server
Listens for commands from the C# desktop app
"""

import asyncio
import grpc
import logging
import sys
import os
from concurrent import futures

# Add the grpc_server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import generated protobuf code
import orchestrator_pb2
import orchestrator_pb2_grpc

# Add project root for JARVIS import
sys.path.insert(0, "G:\\JARVIS_AI_OS")

from python.moa.orchestrator import JARVIS

class OrchestratorServicer(orchestrator_pb2_grpc.OrchestratorServicer):
    """Handles gRPC requests from the C# desktop app"""

    def __init__(self):
        self.jarvis = JARVIS()
        self.sessions = {}

    def ProcessCommand(self, request, context):
        """Process a single command and return response"""
        try:
            command = request.command
            user_id = request.user_id
            session_id = request.session_id or "default"

            logging.info(f"Received command from {user_id}: {command}")

            # Process command
            response_text = self.jarvis.process_command(command)

            return orchestrator_pb2.CommandResponse(
                response=response_text,
                status="success",
                logs=[f"Command '{command}' processed successfully"]
            )

        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return orchestrator_pb2.CommandResponse(
                response=f"Error: {str(e)}",
                status="error",
                logs=[f"Error: {str(e)}"]
            )

    def StreamCommand(self, request, context):
        """Process command and stream responses in real-time"""
        try:
            command = request.command
            user_id = request.user_id

            logging.info(f"Streaming command from {user_id}: {command}")

            # Simulate streaming response
            yield orchestrator_pb2.CommandResponse(
                response=" Processing...",
                status="processing",
                logs=["Started processing"]
            )

            # Process command
            response_text = self.jarvis.process_command(command)

            yield orchestrator_pb2.CommandResponse(
                response=response_text,
                status="success",
                logs=["Command completed"]
            )

        except Exception as e:
            logging.error(f"Error streaming command: {e}")
            yield orchestrator_pb2.CommandResponse(
                response=f"Error: {str(e)}",
                status="error",
                logs=[f"Error: {str(e)}"]
            )


def serve():
    """Start the gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    orchestrator_pb2_grpc.add_OrchestratorServicer_to_server(
        OrchestratorServicer(), server
    )

    port = 50051
    server.add_insecure_port(f'[::]:{port}')
    server.start()

    logging.info(f" JARVIS gRPC Server started on port {port}")
    logging.info(f" Listening on localhost:{port}")
    logging.info("Press Ctrl+C to stop")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    serve()
