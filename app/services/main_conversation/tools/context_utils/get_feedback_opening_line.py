def get_feedback_opening_line(score: int) -> str:
    """
    Generate an appropriate opening line for interview feedback based on score.
    Maintains encouragement while being honest about performance levels.
    """
    if score >= 9:
        return f"Excellent response! You scored {score}/10. "
    elif score >= 7:
        return f"Good job on your answer! You scored {score}/10. "
    elif score >= 5:
        return f"You're on the right track, but there's room for improvement. You scored {score}/10. "
    elif score >= 3:
        return f"Your response needs significant development. You scored {score}/10. "
    else:
        return f"This response requires much more detail and structure. You scored {score}/10. "
