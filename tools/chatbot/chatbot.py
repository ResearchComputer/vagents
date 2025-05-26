import discord
import aiohttp
import asyncio
import os
import json
import uuid  # Added import

# Get environment variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
V1_RESPONSES_URL: str = "http://localhost:8001/v1/responses"
MAX_MESSAGE_LENGTH = 2000 # Discord's max message length is 2000

if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

async def send_chunked_message(destination, content, existing_message=None):
    """Sends or edits a message, chunking it if it exceeds MAX_MESSAGE_LENGTH."""
    if not content: # Don't send empty messages
        return existing_message

    message_to_return = existing_message
    for i in range(0, len(content), MAX_MESSAGE_LENGTH):
        chunk = content[i:i + MAX_MESSAGE_LENGTH]
        if message_to_return and i == 0: # First chunk, edit if possible
            await message_to_return.edit(content=chunk)
        else: # Subsequent chunks or new message
            message_to_return = await destination.send(chunk)
    return message_to_return


# Replaced existing on_message function with this new version
@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    print(f"client.user: {client.user}, message.author: {message.author}, is_dm: {is_dm}")
    should_respond = client.user.mentioned_in(message) or is_dm

    if not should_respond:
        return

    # Extract query, removing mention if present
    query = message.content
    if client.user.mentioned_in(message):
        # Remove bot mention from the query (both with and without nickname)
        mention_pattern_id = f"<@{client.user.id}>"
        mention_pattern_nickname = f"<@!{client.user.id}>"
        query = query.replace(mention_pattern_id, "").replace(mention_pattern_nickname, "").strip()

    if not query:
        await message.channel.send("Please provide a message for me to process.")
        return

    # Determine where to send responses (original channel or new thread)
    response_destination = message.channel
    initial_thread_greeting_message = None  # To track if the "thread created" message was sent

    # If in a server's text channel, try to create a thread
    if isinstance(message.channel, discord.TextChannel):
        thread_name = f"Chat: {query[:50]}" if query else f"Chat with {message.author.name}"
        # Ensure thread name is not empty if query is very short or empty
        if not thread_name.strip():
            thread_name = f"Conversation with {message.author.name}"

        try:
            # Create a public thread from the user's message.
            thread = await message.create_thread(name=thread_name)
            response_destination = thread  # Bot responses will go into this new thread
            initial_thread_greeting_message = await response_destination.send(
                f"Hi {message.author.mention}, I've created this thread for our discussion!"
            )
        except discord.Forbidden:
            await message.channel.send("I lack permissions to create a thread here. Replying in the channel.")
        except discord.HTTPException as e:
            await message.channel.send(f"Couldn't create a thread (Error: {e}). Replying in the channel.")
        # If thread creation fails, response_destination remains message.channel

    # Start typing indicator in the determined response destination
    typing_task = asyncio.create_task(send_typing_indicator(response_destination))

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "id": str(uuid.uuid4()),  # Unique ID for each API request
                "module": "vagents.contrib.modules.chat:AgentChat",
                "input": query,
                "stream": True,
                "additional": {"round_limit": 3},
            }
            async with session.post(V1_RESPONSES_URL, json=payload) as resp:
                if resp.status == 200:
                    api_response_message_object = None  # Stores the Discord message object for API stream

                    async for line in resp.content:
                        if line:
                            data_str = line.decode("utf-8").strip()
                            if data_str.startswith("data: "):  # Handle SSE "data: " prefix
                                data_str = data_str[len("data: ") :]
                            if not data_str:  # Skip empty lines from stream
                                continue

                            try:
                                json_data = json.loads(data_str)
                                content_part_to_send = None

                                msg_type = json_data.get("type")

                                if msg_type == "tool_call":
                                    content_part_to_send = f"I'm using the tool: [{json_data.get('name', 'Unknown tool')}]"
                                elif msg_type == "tool_result":
                                    content_part_to_send = f"I got the result from the tool:\n\n[{json_data.get('name', 'Unknown tool')}]: {json_data.get('result', 'No result')}"
                                else:
                                    # Attempt to extract chat content from common fields (e.g., 'content', 'delta', 'text')
                                    # This part might need adjustment based on your API's actual response structure for chat messages
                                    chat_content = json_data.get("content") or json_data.get("delta") or json_data.get("text")
                                    if isinstance(chat_content, str):
                                        content_part_to_send = chat_content
                                    else:  # Log if content is not in expected format or type
                                        print(f"Stream data (not directly sent to Discord as chat): {json_data}")

                                if content_part_to_send:
                                    if msg_type == "tool_call" or not api_response_message_object:
                                        # Send a new message for tool_call or if it's the first content part from API
                                        api_response_message_object = await send_chunked_message(response_destination, content_part_to_send)
                                    elif api_response_message_object:
                                        # Edit existing message for tool_result or subsequent chat content parts
                                        # For streaming actual chat, you might want to append content:
                                        # current_content = api_response_message_object.content
                                        # await send_chunked_message(response_destination, current_content + content_part_to_send, existing_message=api_response_message_object)
                                        # For now, it replaces content, similar to tool_result behavior.
                                        await send_chunked_message(response_destination, content_part_to_send, existing_message=api_response_message_object)

                            except json.JSONDecodeError:
                                print(f"Stream: Failed to decode JSON: {data_str}")
                            except discord.HTTPException as e:  # Errors sending/editing Discord message
                                print(f"Discord API error during stream: {e}")
                                # Notify user in the channel about the update issue
                                await response_destination.send(f"There was an error updating my response: {e}")
                                break  # Stop processing this stream
                            except Exception as e:  # Other errors during stream processing
                                print(f"Stream processing error: {e}")
                                break  # Stop processing this stream

                    # After stream, if no API response message was sent and no initial thread greeting was sent
                    if not api_response_message_object and not initial_thread_greeting_message:
                        await send_chunked_message(response_destination, "I received an empty response or couldn't process it.")

                else:  # API returned non-200 status
                    error_text = await resp.text()
                    await send_chunked_message(response_destination,
                        f"Error from API: {resp.status} - {error_text[:1000]}"  # Truncate long errors
                    )
    except aiohttp.ClientConnectorError as e:  # Connection error to the API
        await send_chunked_message(response_destination, f"I couldn't connect to my services: {e}")
    except discord.Forbidden:
        if response_destination != message.channel:
            await send_chunked_message(message.channel, "I lost permission to send messages in the thread. Please try again in the main channel.")
        else:  # Error was in the original channel itself
            await send_chunked_message(message.channel, "I don't have permission to send messages here.")
    except Exception as e:  # Catch-all for other unexpected errors in the handler
        print(f"Unexpected error in on_message handler: {e}")  # Log detailed error to console
        # Send a generic error message to Discord, possibly with a short error detail
        await send_chunked_message(response_destination, f"An unexpected error occurred. Please try again later. (Details: {str(e)[:200]})")
    finally:
        typing_task.cancel()  # Ensure typing indicator is stopped


async def send_typing_indicator(channel):
    try:
        while True:
            await channel.typing()
            await asyncio.sleep(5)  # Discord's typing indicator lasts for 10 seconds
    except asyncio.CancelledError:
        pass  # Task was cancelled, normal operation


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
