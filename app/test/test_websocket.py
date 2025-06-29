import asyncio
import websockets
import json
import pytest
from app.services.main_conversation.tools.question_utils.get_questions import get_questions

jobRole = "Software Engineer"
jobLevel = "entry"
questionType = "behavioral"

@pytest.mark.asyncio
async def test_get_questions():
    """Test that we can fetch questions from the database"""
    result = await get_questions(
        jobRole=jobRole,
        jobLevel=jobLevel,
        questionType=questionType
    )
    
    assert result["success"] is True, "Failed to fetch questions from database"
    assert result["count"] > 0, "No questions found in database"
    assert len(result["questions"]) > 0, "Questions list is empty"
    
    # Print the first question for verification
    print("\nFirst question from database:", result["questions"][0])
    
    return result

@pytest.mark.asyncio
async def test_websocket():
    # First verify we can get questions
    questions_result = await test_get_questions()
    
    uri = "ws://127.0.0.1:8000/api/ws"
    async with websockets.connect(uri) as websocket:
        # Send initial session setup
        await websocket.send(json.dumps({
            "session_id": "123",
            "user_name": "Kent Hudson Caparas",
            "jobRole": jobRole,
            "jobLevel": jobLevel,
            "questionType": questionType
        }))
        
        # Get initial response
        response = await websocket.recv()
        print("\nInitial response:", response)
        
        # Send a message
        await websocket.send(json.dumps({
            "content": "Yes, I am ready!"
        }))
        
        # Get response
        response = await websocket.recv()
        print("\nResponse after ready:", response)
        
        # Verify that the response contains one of our actual questions
        response_data = json.loads(response)
        assert any(question in response_data["content"] for question in questions_result["questions"]), \
            "Response does not contain any of the actual questions from the database"

        await websocket.send(json.dumps({
            "type": "message",
            "content": json.dumps({
                "jobRole": jobRole,
                "jobLevel": jobLevel,
                "questionType": questionType,
                "interviewType": questionType,
                "question": questions_result["questions"][0],
                "answer": "During my capstone project, I served as project coordinator and lead backend developer for a 5-person team building an e-commerce platform for a local nonprofit, where I managed timelines, designed the database architecture, and mentored a struggling team member through Node.js development. When we encountered a major payment integration issue three weeks before deadline, I researched solutions, coordinated with frontend developers to implement Stripe, and initiated daily standups to keep us on track. We delivered on time with full functionality, received the top grade in our class, and the nonprofit continued using our platform - plus the team member I mentored gained enough confidence to land a developer internship."
            })
        }))

        response = await websocket.recv()
        print("\nResponse after answer 1:", response)

        # wait for 2 seconds
        await asyncio.sleep(2)
        
        await websocket.send(json.dumps({
            "type": "message",
            "content": json.dumps({
                "jobRole": jobRole,
                "jobLevel": jobLevel,
                "questionType": questionType,
                "interviewType": questionType,
                "question": questions_result["questions"][1],
                "answer": "When our production API started experiencing intermittent 500 errors with no clear pattern in the logs, affecting about 15% of user requests, I systematically approached the problem by first reproducing it in our staging environment, then methodically checking each system component - database connections, memory usage, and third-party service calls - while documenting my findings and collaborating with the DevOps team to analyze server metrics. Through this process, I discovered that a recent code deployment had introduced a race condition in our caching layer that only manifested under high concurrent load. Within 48 hours, I implemented a thread-safe solution and established additional monitoring alerts, which reduced our error rate to under 0.1% and prevented similar issues from reaching production in the future."
            })
        }))

        response = await websocket.recv()
        print("\nResponse after answer 2:", response)
