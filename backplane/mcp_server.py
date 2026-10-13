"""The backplane's MCP server: the tools an agent calls on a person's behalf.

Runs locally over stdio, as the person signed in to the CLI for Microsoft 365 in this environment.
It holds no keys of its own. Tool input schemas come from the LinkML model (via the generated classes),
so an agent cannot open a deal room without the fields the model requires.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import deal_room
from .generated import DealRoomRequest
from .model import load

server = MCPServer(
    "contoso-backplane",
    instructions=(
        "Tools for Contoso Capital's governed workspace. Ask the user for any required field they did not "
        "give; never guess a sensitivity. Report refusals exactly as returned, including the rule name."
    ),
)


def create_deal_room(request: DealRoomRequest) -> dict:
    """Open a deal room for a new deal: a private Microsoft 365 group and SharePoint site with the
    deal team as members, tagged with the deal's domain, name and sensitivity, optionally filing the
    attachments of an email (e.g. the CIM) into it. Runs as the person asking and obeys the firm's rules."""
    return deal_room.create(load(), request)


server.add_tool(create_deal_room, name="create_deal_room")

if __name__ == "__main__":
    server.run("stdio")
