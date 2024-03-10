import re

def format_links_for_slack(text):
    # Regex pattern to identify URLs
    url_pattern = r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)'
    formatted_text = re.sub(url_pattern, r'<\1|Link>', text)  # Replace URLs with Slack formatted links

def convert_markdown_links_to_slack(text):
    # Convert bold text
    text = text.replace("**", "*")

    # Convert lists
    text = re.sub(r"\n- ", "\n• ", text)

    # Handle placeholder video links
    placeholder_video_links = re.findall(r'\[Watch Video\]\(Watch Video\)', text)
    for placeholder in placeholder_video_links:
        # Here you could insert a message indicating the video link is not available
        # Or replace it with an actual video link if you have a way to map the topics to video URLs
        message = "Video link not available"
        text = text.replace(placeholder, message)

    # General pattern for URLs
    urls = re.findall(r'http[s]?://[^\s]+', text)
    for url in urls:
        slack_link = f"<{url}>"
        text = text.replace(url, slack_link)

    return text

def convert_to_slack_formatting(text):
    # Convert Markdown links to Slack format
    text = re.sub(r'\[([^\]]+)\]\((http[s]?://[^)]+)\)', r'<\2|\1>', text)

    # Replace double asterisks with single for bold formatting in Slack
    text = text.replace("**", "*")
    return text
