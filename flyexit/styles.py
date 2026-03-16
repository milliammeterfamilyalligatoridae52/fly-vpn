"""Textual CSS styles for the Fly VPN app."""

APP_CSS = """\
Screen {
    background: $surface;
}

#main {
    margin: 1 2;
}

#controls {
    height: auto;
    padding: 1 2;
    background: $panel;
    border: tall $primary;
    margin-bottom: 1;
}

#region-row {
    height: 3;
    align: left middle;
}

#region-row Label {
    margin: 0 1 0 0;
    text-style: bold;
    width: auto;
}

#region-select {
    width: 40;
}

#button-row {
    height: auto;
    margin-top: 1;
    align: center middle;
}

#btn-launch {
    margin: 0 1;
}

#btn-stop {
    margin: 0 1;
}

#status-bar {
    height: 1;
    margin: 0 0 1 0;
    text-align: center;
    color: $text-muted;
    text-style: italic;
}

#log-box {
    border: tall $accent;
    height: 1fr;
    min-height: 10;
}
"""
