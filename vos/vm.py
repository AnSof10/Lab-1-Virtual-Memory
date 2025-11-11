from dataclasses import dataclass
from collections import deque
from typing import Dict, Deque, List, Optional

PAGE_SIZE = 256
VIRTUAL_PAGES = 16
PHYSICAL_FRAMES = 8


@dataclass
class PTEntry:
    """
    Page Table Entry for a single virtual page.

    - frame: physical frame number where the page is loaded, or None if the
      page is currently not in RAM.
    - present: True if the page is currently resident in physical memory.
    - dirty: True if the page has been modified in RAM and must be written
      back to the backing store when evicted.
    """
    frame: Optional[int] = None
    present: bool = False
    dirty: bool = False


class PageTable:
    """
    Page table that maps virtual page numbers (0 .. VIRTUAL_PAGES - 1)
    to PTEntry objects.
    """

    def __init__(self) -> None:
        # Create one PTEntry per virtual page.
        self.entries: Dict[int, PTEntry] = {
            page_no: PTEntry() for page_no in range(VIRTUAL_PAGES)
        }

    def get(self, page_no: int) -> PTEntry:
        """
        Return the PTEntry for the given virtual page number.

        Raises ValueError if the page number is out of range.
        """
        if page_no < 0 or page_no >= VIRTUAL_PAGES:
            raise ValueError(f"Page number {page_no} out of range "
                             f"(0 .. {VIRTUAL_PAGES - 1})")
        return self.entries[page_no]


class PhysicalMemory:
    """
    Representation of physical memory as a fixed number of frames.

    Each frame is a bytearray of length PAGE_SIZE.
    A simple free-frame list is used to keep track of which frames
    are available for allocation.
    """

    def __init__(self) -> None:
        # Allocate PHYSICAL_FRAMES frames of size PAGE_SIZE.
        self.frames: List[bytearray] = [
            bytearray(PAGE_SIZE) for _ in range(PHYSICAL_FRAMES)
        ]
        # Queue of free frame indices.
        self.free_frames: Deque[int] = deque(range(PHYSICAL_FRAMES))

    def has_free_frame(self) -> bool:
        """Return True if there is at least one free frame."""
        return len(self.free_frames) > 0

    def alloc_frame(self) -> int:
        """
        Allocate and return a free frame number.

        Raises RuntimeError if no free frames are available.
        """
        if not self.free_frames:
            raise RuntimeError("No free frames available")
        return self.free_frames.popleft()

    def free_frame(self, frame_no: int) -> None:
        """
        Mark a frame as free so it can be reused later.
        """
        self.free_frames.append(frame_no)

    def read_byte(self, frame_no: int, offset: int) -> int:
        """
        Read a single byte from the given frame and offset.
        """
        return self.frames[frame_no][offset]

    def write_byte(self, frame_no: int, offset: int, value: int) -> None:
        """
        Write a single byte to the given frame and offset.
        Only the low 8 bits of value are stored.
        """
        self.frames[frame_no][offset] = value & 0xFF
