
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

BOOKMARKS_FILE = "data/chat_bookmarks.json"

def ensure_bookmarks_file():
    """Ensure the bookmarks file exists and is valid JSON."""
    os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
    if not os.path.exists(BOOKMARKS_FILE):
        with open(BOOKMARKS_FILE, "w") as f:
            json.dump([], f)

def get_all_bookmarks() -> List[Dict[str, Any]]:
    """Fetch all bookmarked chats."""
    ensure_bookmarks_file()
    try:
        with open(BOOKMARKS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_bookmark(title: str, messages: List[Dict[str, Any]]) -> str:
    """
    Save a chat session as a bookmark.
    
    Args:
        title: User-provided or auto-generated title for the bookmark
        messages: The list of message dictionaries from st.session_state.messages
        
    Returns:
        The ID of the newly created bookmark
    """
    ensure_bookmarks_file()
    bookmarks = get_all_bookmarks()
    
    bookmark_id = str(uuid.uuid4())
    
    # Pre-process messages to handle DataFrames (convert to dict/list)
    serializable_messages = []
    for msg in messages:
        msg_copy = msg.copy()
        if "dataframe" in msg_copy and msg_copy["dataframe"] is not None:
            # Convert DataFrame to records for JSON serialization
            msg_copy["dataframe"] = msg_copy["dataframe"].to_dict(orient="records")
        serializable_messages.append(msg_copy)
    
    new_bookmark = {
        "id": bookmark_id,
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "messages": serializable_messages
    }
    
    bookmarks.append(new_bookmark)
    
    with open(BOOKMARKS_FILE, "w") as f:
        json.dump(bookmarks, f, indent=2)
        
    return bookmark_id

def delete_bookmark(bookmark_id: str) -> bool:
    """Delete a bookmark by ID."""
    bookmarks = get_all_bookmarks()
    initial_count = len(bookmarks)
    bookmarks = [b for b in bookmarks if b["id"] != bookmark_id]
    
    if len(bookmarks) < initial_count:
        with open(BOOKMARKS_FILE, "w") as f:
            json.dump(bookmarks, f, indent=2)
        return True
    return False

def get_bookmark(bookmark_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a specific bookmark by ID."""
    bookmarks = get_all_bookmarks()
    for b in bookmarks:
        if b["id"] == bookmark_id:
            # Convert records back to DataFrames for use in Streamlit
            import pandas as pd
            for msg in b["messages"]:
                if "dataframe" in msg and msg["dataframe"] is not None:
                    msg["dataframe"] = pd.DataFrame(msg["dataframe"])
            return b
    return None
