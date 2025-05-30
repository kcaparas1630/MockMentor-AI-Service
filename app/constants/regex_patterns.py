import re

# Compile regex patterns once for better performance
REGEX_PATTERNS = {
    'feedback': re.compile(r"[\"']feedback[\"']\s*:\s*[\"'](.*?)[\"']", re.DOTALL),
    'strengths': re.compile(r"[\"']strengths[\"']\s*:\s*\[(.*?)\]", re.DOTALL),
    'improvements': re.compile(r"[\"']improvements[\"']\s*:\s*\[(.*?)\]", re.DOTALL),
    'score': re.compile(r"[\"']score[\"']\s*:\s*(\d+)"),
    'tips': re.compile(r"[\"']tips[\"']\s*:\s*\[(.*?)\]", re.DOTALL)
}
