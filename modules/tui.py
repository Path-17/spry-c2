from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Input, Label
from textual.containers import VerticalScroll, Horizontal
from datetime import datetime
from . import client_globals # Global db to track activity\
from . import commands
import asyncio
import requests.exceptions



# Where server updates are displayed
class ServerLog(VerticalScroll):
    def add_log(self, text: str):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        self.mount(Label(f"{dt_string}: {text}"))
        self.scroll_end()
# Where command output is displayed
# either directly from the client (like input errors)
# or from the implant responding to a command
class CommandOutput(VerticalScroll):
    def print(self, text):
        self.mount(Label(text))
        self.scroll_end()
    def err_generic(self, text):
        self.mount(Label(text))
        self.scroll_end()
# Input box at the bottom of the TUI
class CommandInput(Input):
    def clear(self):
        self.value = ""
    def log_output(self, text: str):
        self.app.get_widget_by_id("command_output").print(text)
    def log_error(self, text: str):
        self.app.get_widget_by_id("command_output").print(text)
    def action_submit(self):
        # Parse the command
        to_parse = self.value.strip()
        args = ' '.join(to_parse.split())
        args = args.split(' ')

        # Call the function associated with the args[0] from the 
        # CMD_TABLE using the args[1:] slice and pass the client app as well
        # so the function can handle the associated success output / edit the app
        try:
            commands.CMD_TABLE[args[0]](args, self.app)
        # TODO: Create an error exception table with functions as well
        except Exception as err:
            self.log_error("Exception: {}".format(type(err).__name__))
            self.log_error("Exception message: {}".format(err))

        # Clear input box and exit
        self.clear()
        return

# The actual client, also implements the server update functionality
# with an asyncio task that checks for the server update flag
# in the global 
class Client(App):
    CSS_PATH = "client.css" 
    async def server_update(self):
        while True:
            await asyncio.sleep(3)
            if client_globals.instance_db.new_server_update == True:
                # TODO: Process the update
               client_globals.instance_db.new_server_update = False
    def on_mount(self):
        asyncio.create_task(self.server_update())
    def compose(self) -> ComposeResult:
        # Initialize the TUI
        with Horizontal():
            server_logs = ServerLog(id="server_logs")
            server_logs.border_title = "Server Logs"
            yield server_logs
            server_logs.add_log(f"Successfully connected to C1.5 server {client_globals.instance_db.server}:{client_globals.instance_db.port} as \'{client_globals.instance_db.operator_name}\'")
        command_output = CommandOutput(id="command_output")
        command_output.border_title = "Command Output - No Implant Selected"
        yield command_output
        yield CommandInput(placeholder="Input commands here, 'help' for available commands", id="command_input")
