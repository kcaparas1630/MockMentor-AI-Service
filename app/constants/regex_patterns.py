import re

# Compile regex patterns once for better performance
REGEX_PATTERNS = {
    'overall': re.compile(r"[\"']overall_assessment[\"']\s*:\s*[\"'](.*?)[\"']", re.DOTALL),
    'strengths': re.compile(r"[\"']strengths[\"']\s*:\s*\[(.*?)\]", re.DOTALL),
    'areas': re.compile(r"[\"']areas_for_improvement[\"']\s*:\s*\[(.*?)\]", re.DOTALL),
    'score': re.compile(r"[\"']confidence_score[\"']\s*:\s*(\d+)"),
    'actions': re.compile(r"[\"']recommended_actions[\"']\s*:\s*\[(.*?)\]", re.DOTALL)
}
