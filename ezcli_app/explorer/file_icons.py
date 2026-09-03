"""File type to emoji icon mapper for EasyCLI v0.2."""

import os
from pathlib import Path


IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".bmp", ".ico", ".tiff", ".tif", ".heic", ".raw"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".alac", ".aiff", ".opus", ".mid", ".midi"
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".3gp", ".mpeg", ".mpg", ".ts"
}

ARCHIVE_EXTENSIONS = {
    ".zip", ".tar", ".gz", ".xz", ".bz2", ".deb", ".rpm", ".7z", ".rar", ".iso", ".tgz", ".zst"
}

TEXT_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".doc", ".docx", ".rtf", ".odt", ".epub", ".rst", ".tex", ".csv", ".tsv"
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".sass", ".less",
    ".sh", ".bash", ".zsh", ".fish", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".rs", ".go", ".java", ".kt", ".swift", ".php", ".rb", ".pl", ".pm", ".lua",
    ".json", ".sql", ".dart", ".r", ".scala", ".clj", ".ex", ".exs", ".vim"
}

LOG_EXTENSIONS = {
    ".log", ".journal", ".out", ".err", ".trace"
}

CONFIG_EXTENSIONS = {
    ".conf", ".cfg", ".ini", ".toml", ".yaml", ".yml", ".env", ".xml", ".properties",
    ".rc", ".service", ".socket", ".timer", ".desktop"
}


def get_file_icon(path_or_name: str, is_dir: bool = False) -> str:
    """Return appropriate single-character emoji icon based on file type."""
    if is_dir:
        return "📁"

    name = os.path.basename(path_or_name).lower()

    # Specific well-known filenames
    if name in {"dockerfile", "makefile", "gemfile", "cmakelists.txt"}:
        return "💻"
    if name.startswith(".env") or name in {"config", ".gitconfig", ".bashrc", ".zshrc"}:
        return "⚙️"
    if name.endswith("license") or name == "readme":
        return "📄"

    _, ext = os.path.splitext(name)

    if ext in IMAGE_EXTENSIONS:
        return "🖼️"
    if ext in AUDIO_EXTENSIONS:
        return "🎵"
    if ext in VIDEO_EXTENSIONS:
        return "🎬"
    if ext in ARCHIVE_EXTENSIONS:
        return "📦"
    if ext in TEXT_EXTENSIONS:
        return "📄"
    if ext in CODE_EXTENSIONS:
        return "💻"
    if ext in LOG_EXTENSIONS:
        return "📜"
    if ext in CONFIG_EXTENSIONS:
        return "⚙️"

    return "❓"
