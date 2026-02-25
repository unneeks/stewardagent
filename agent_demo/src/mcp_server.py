import sys
import json
import logging
from src.reviewer import CodeReviewer

# Setup basic error logging so we don't mess up stdout which is for MCP JSON-RPC
logger = logging.getLogger("mcp")
fh = logging.FileHandler("mcp_server.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)


def send_response(response_obj):
    """Write standard JSON RPC back to the IDE via stdout."""
    sys.stdout.write(json.dumps(response_obj) + "\n")
    sys.stdout.flush()
    logger.debug(f"SENT: {json.dumps(response_obj)}")

def handle_message(message_str):
    try:
        msg = json.loads(message_str)
        logger.debug(f"RECEIVED: {msg}")
    except json.JSONDecodeError:
        return

    msg_id = msg.get("id")
    method = msg.get("method")
    
    if method == "initialize":
        # Handshake with IDE
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05", # Standard
                "serverInfo": {
                    "name": "StewardAgent Server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {} # Expose tools capability
                }
            }
        })
    elif method == "notifications/initialized":
        # IDE acknowledged handshake, nothing to send back
        pass
        
    elif method == "tools/list":
        # IDE asks what tools we have available
        send_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "review_changeset",
                        "description": "Reviews code (SQL) or policy changes using the Steward Agent Semantic Governance AI. It checks downstream/upstream lineage against the data ontology, parses the risk using an LLM, and creates enforcement suggestions.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "pr_title": {
                                    "type": "string",
                                    "description": "A title for this change."
                                },
                                "changeset_type": {
                                    "type": "string",
                                    "enum": ["code", "policy"],
                                    "description": "Are they changing an sql 'code' model, or a 'policy' business term?"
                                },
                                "changed_entity": {
                                    "type": "string",
                                    "description": "The exact name of the entity modified, e.g. 'gold_fct_approvals' or 'BT_001'."
                                },
                                "diff_text": {
                                    "type": "string",
                                    "description": "The unified diff containing the changes."
                                }
                            },
                            "required": ["pr_title", "changeset_type", "changed_entity", "diff_text"]
                        }
                    }
                ]
            }
        })
        
    elif method == "tools/call":
        # IDE AI is asking us to run a tool
        params = msg.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "review_changeset":
            logger.debug(f"Calling CodeReviewer for {args}")
            try:
                # The reviewer natively uses Gemini to reason code changes to business term linking and rules
                reviewer = CodeReviewer()
                
                # The reviewer writes a markdown file to disk containing the AI report
                reviewer.review_changeset(
                    pr_title=args.get("pr_title"),
                    changeset_type=args.get("changeset_type"),
                    changed_entity=args.get("changed_entity"),
                    diff_text=args.get("diff_text")
                )
                
                # We read the generated report to pass it back to the IDE
                with open("pr_review_report.md", "r") as f:
                    report_text = f.read()
                    
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Steward Agent successfully reviewed the change!\\n\\n{report_text}"
                            }
                        ]
                    }
                })
            except Exception as e:
                logger.error(f"Error running reviewer: {e}")
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                })

def start():
    logger.info("Starting up MCP JSON-RPC Server...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            handle_message(line)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break

if __name__ == "__main__":
    start()
