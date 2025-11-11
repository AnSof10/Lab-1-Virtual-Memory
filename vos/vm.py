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
            raise ValueError(
                f"Page number {page_no} out of range (0 .. {VIRTUAL_PAGES - 1})"
            )
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


class VM:
    """
    Virtual Memory simulator using:
    - a single page table
    - a backing store (simulated disk)
    - FIFO page replacement
    """

    def __init__(self) -> None:
        # Page table and physical memory
        self.page_table = PageTable()
        self.phys_mem = PhysicalMemory()

        # Backing store: one "disk page" per virtual page
        self.backing_store: List[bytearray] = [
            bytearray(PAGE_SIZE) for _ in range(VIRTUAL_PAGES)
        ]

        # Reverse mapping: frame -> page
        self.frame_to_page: Dict[int, int] = {}

        # FIFO queue for replacement (contains frame numbers)
        self.fifo_queue: Deque[int] = deque()

    def _ensure_in_ram(self, page_no: int) -> int:
        """
        Ensure that the given virtual page is loaded in a physical frame.

        If the page is already present in RAM, return its frame number.
        Otherwise, handle a page fault:
          - allocate a free frame, OR
          - evict a frame using FIFO (writing back if the victim is dirty),
        then load the requested page into that frame and update the page table.
        """
        # 1) Validate page number
        if page_no < 0 or page_no >= VIRTUAL_PAGES:
            raise ValueError(
                f"Page number {page_no} out of range (0 .. {VIRTUAL_PAGES - 1})"
            )

        # 2) Look up the page table entry
        entry = self.page_table.get(page_no)

        # 3) If already present, just return its frame
        if entry.present and entry.frame is not None:
            return entry.frame

        # 4) Page fault: we need to obtain a physical frame
        if self.phys_mem.has_free_frame():
            # There is at least one free frame we can use
            frame = self.phys_mem.alloc_frame()
        else:
            # No free frames – we must evict a page using FIFO
            victim_frame = self.fifo_queue.popleft()

            # Find which page is currently stored in this frame
            victim_page = self.frame_to_page[victim_frame]
            victim_entry = self.page_table.get(victim_page)

            # If the victim page is dirty, write it back to the backing store
            if victim_entry.dirty and victim_entry.frame is not None:
                self.backing_store[victim_page][:] = \
                    self.phys_mem.frames[victim_frame]

            # Mark the victim page as not present and clean
            victim_entry.present = False
            victim_entry.frame = None
            victim_entry.dirty = False

            # We will reuse victim_frame for the new page
            frame = victim_frame

        # 5) Load the requested page from the backing store into the chosen frame
        self.phys_mem.frames[frame][:] = self.backing_store[page_no]

        # 6) Update the page table entry for the requested page
        entry.frame = frame
        entry.present = True
        entry.dirty = False  # freshly loaded from backing store

        # 7) Update the reverse mapping and FIFO queue
        self.frame_to_page[frame] = page_no
        if frame not in self.fifo_queue:
            self.fifo_queue.append(frame)

        # 8) Return the frame number where the page is now loaded
        return frame
