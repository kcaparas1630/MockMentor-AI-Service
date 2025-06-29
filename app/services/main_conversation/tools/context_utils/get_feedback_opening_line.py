def get_feedback_opening_line(score: int) -> str:
    if score >= 9:
        return f"I like your answer, that was great! You scored {score}/10. "
    elif score >= 6:
        return f"Great effort on your response! You scored {score}/10. "
    elif score >= 4:
        return f"Good attempt, but you can do better. You scored {score}/10. "
    else:
        return f"I'm sorry, maybe you can answer that question better.You scored {score}/10. "
