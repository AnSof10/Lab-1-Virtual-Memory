# Virtual Memory – From Concept to Simulation

## 1. Virtual vs. Physical Memory

Physical memory is the actual RAM installed in a computer: a finite set of bytes addressed by the hardware. Processes, however, are written as if they had access to a large, continuous address space that starts at address 0. Virtual memory is the abstraction that gives each process its own private address space, independent of the physical RAM size and layout.

The operating system and the Memory Management Unit (MMU) translate virtual addresses (used by processes) into physical addresses (used by RAM). This has several benefits:

- **Convenience for programmers**: each process believes it has a simple, contiguous memory space.
- **Protection**: one process cannot directly access another process’s memory.
- **Flexibility**: the OS can run programs that are larger than RAM by keeping some parts on disk and bringing them into memory on demand.

In short, virtual memory decouples the logical view of memory from the physical hardware that stores it.

## 2. Paging & Page Tables

Most modern systems implement virtual memory using **paging**. The virtual address space is divided into fixed-size blocks called **pages** (for example, 4 KiB each). Physical memory is divided into blocks of the same size called **frames**.

A virtual address is conceptually split into:

- **Page number**: which virtual page we are accessing.
- **Offset**: the position inside that page.

The OS maintains a **page table** for each process. The page table maps each virtual page number to:

- A physical frame number (if the page is currently in RAM).
- Or a marker indicating that the page is not present (and possibly where to load it from).

Each page table entry usually includes bits such as:

- **Present bit**: indicates if the page is currently loaded in RAM.
- **Dirty bit**: indicates if the page has been modified in memory.
- **Access permissions**: read / write / execute.
- **Reference bit**: used by some replacement algorithms.

In our lab, we simplify this to a small number of virtual pages and physical frames and use a minimal page table entry structure.

## 3. Page Fault Handling

A **page fault** occurs when a process accesses a virtual page whose “present” bit in the page table is 0, meaning the page is not currently in RAM. This triggers a controlled exception:

1. The hardware traps into the operating system (page fault exception).
2. The OS checks whether the access is valid:
   - If the process accessed an illegal address, the OS terminates the process (segmentation fault).
   - If the address is valid but the page is simply not in memory, the OS must bring it in.
3. To bring the page into RAM, the OS:
   - Finds a free physical frame; if none exist, chooses a victim frame to evict using a page replacement algorithm (like FIFO or LRU).
   - If the victim page is dirty, writes it back to disk.
   - Loads the requested page from disk (backing store) into the chosen frame.
   - Updates the page table so the virtual page now points to that frame and marks it present.
4. The OS then restarts the instruction that caused the fault, and this time the access succeeds.

In our simulation, the method `_ensure_in_ram(page_no)` will roughly perform these steps in software.

## 4. Backing Store & Dirty Bit

Because RAM is limited, not all pages can reside in memory at the same time. The **backing store** (typically a swap file or a paging area on disk) holds the full contents of all pages for a process. When a page is evicted from RAM, its data may need to be written back to the backing store so nothing is lost.

This is where the **dirty bit** is essential:

- When a page is loaded from disk, it initially matches the backing store contents, so the dirty bit is cleared.
- When the CPU (or our simulator) writes to that page, the dirty bit is set to 1, meaning the in-memory copy has diverged from the disk copy.
- If the OS later decides to evict that page from RAM:
  - If the dirty bit is 1, the OS must **write the page back** to the backing store before discarding it.
  - If the dirty bit is 0, the page can be discarded without writing, because disk already has the up-to-date data.

Tracking dirtiness avoids unnecessary disk writes while ensuring modified data is never lost. In the lab, our page table entry will include a `dirty` field and we will explicitly write back dirty pages to the simulated backing store when evicting them.

## 5. FIFO Page Replacement

When there is no free frame available and a page fault occurs, the OS must choose a page to evict from RAM. This is the job of the **page replacement algorithm**.

One of the simplest algorithms is **FIFO (First-In, First-Out)**:

- Maintain a queue of frames in the order in which pages were loaded.
- When a new page must be brought into memory and no frames are free, evict the page that has been in memory the longest (the “oldest” page in the queue).

Advantages of FIFO:

- Very simple to implement.
- Low overhead: just a queue of frames.

Disadvantages:

- FIFO does not take into account how frequently or recently a page is used.
- It can evict a heavily used page simply because it was loaded a long time ago.
- It can suffer from **Belady’s anomaly**, where giving a process more frames paradoxically leads to more page faults.

More sophisticated policies, like **LRU (Least Recently Used)** or approximation algorithms, try to keep pages that are actively used in memory. In this lab, we will stick to FIFO for clarity and ease of implementation.

## 6. Address Translation

Address translation is the process of converting a virtual address to a physical address using the page table.

For a simple paged system:

1. Split the virtual address into:
   - `page_no = vaddr // PAGE_SIZE`
   - `offset = vaddr % PAGE_SIZE`
2. Use the page number to index into the page table and obtain the corresponding page table entry.
3. If the present bit is 0, a page fault occurs and the OS (or our simulator) must load the page into RAM.
4. Once present, the page table entry provides the **frame number**.
5. The physical address is then:
   - `phys_addr = frame_no * PAGE_SIZE + offset`

In code, we often don’t construct the combined physical address explicitly; instead, we access the frame array by index (`frame_no`) and use `offset` as an index inside that frame.

Our simulator will implement this mechanism by splitting virtual addresses into `(page_no, offset)` and mapping page numbers to frames through the page table.

## 7. Process Isolation

One of the most powerful features of virtual memory is **process isolation**. Each process is given its own virtual address space and its own page table. The MMU uses the page table associated with the currently running process.

Consequences:

- A process cannot read or write memory belonging to another process, because its page table does not map those virtual addresses to valid frames.
- Bugs in one program are less likely to corrupt the memory of others.
- The kernel can protect its own memory by using page tables and permission bits that user processes cannot modify.

In our lab, we simulate only a **single process**, so we have just one page table and one virtual address space. To support multiple processes, we would keep a separate page table per process and switch the “active” page table on a context switch, just like a real OS does.

## 8. Connection to Software Simulation

A software simulation of virtual memory captures the core ideas of the real hardware and OS mechanism, but runs entirely in user space with regular data structures:

- Our **virtual pages** are represented by indices (0 to VIRTUAL_PAGES-1).
- **Physical frames** are an array of `bytearray` objects with size `PAGE_SIZE`.
- The **page table** is a Python mapping from page numbers to simple entries (`frame`, `present`, `dirty`).
- The **backing store** is another array of `bytearray` objects that represents what would normally be stored on disk.
- The **page fault handler** is implemented as a method (e.g., `_ensure_in_ram`) that loads pages into frames and evicts old ones using FIFO.

By writing and testing this simulator, you practice the logic that a real OS uses to manage memory, but without needing actual hardware support or kernel privileges. This bridges the gap between the abstract theory of virtual memory and the concrete implementation details that make it work.
