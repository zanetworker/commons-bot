import re

def format_links_for_slack(text):
    # Regex pattern to identify URLs
    url_pattern = r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)'
    formatted_text = re.sub(url_pattern, r'<\1|Link>', text)  # Replace URLs with Slack formatted links
    return formatted_text

def convert_markdown_links_to_slack(text):
    # Find all Markdown links in the text
    markdown_links = re.findall(r'\[([^\]]+)\]\((http[s]?://[^)]+)\)', text)

    # Replace each Markdown link with Slack's link format
    for link_text, url in markdown_links:
        slack_link = f"<{url}|{link_text}>"
        markdown_link = f"[{link_text}]({url})"
        text = text.replace(markdown_link, slack_link)

    return text
