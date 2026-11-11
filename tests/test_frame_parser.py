from mordomus import extract_frames

FRAME = bytes([0x49, 0xAA, 0x07, 0x01, 0x46])


def test_single_complete_frame():
    buf = bytearray(FRAME)
    assert extract_frames(buf) == [FRAME]
    assert buf == bytearray()


def test_multiple_frames_in_one_read():
    other = bytes([0x49, 0xAA, 0x08, 0x03, 0x46])
    buf = bytearray(FRAME + other)
    assert extract_frames(buf) == [FRAME, other]
    assert buf == bytearray()


def test_frame_split_across_reads():
    buf = bytearray(FRAME[:3])
    assert extract_frames(buf) == []
    assert buf == bytearray(FRAME[:3]), "partial frame must be kept for the next read"

    buf.extend(FRAME[3:])
    assert extract_frames(buf) == [FRAME]
    assert buf == bytearray()


def test_leading_garbage_is_skipped():
    buf = bytearray(b"\x00\xff\x12" + FRAME)
    assert extract_frames(buf) == [FRAME]


def test_bad_sync_resynchronises_on_next_frame():
    # 0x49 not followed by 0xAA, then a valid frame
    buf = bytearray(bytes([0x49, 0x00]) + FRAME)
    assert extract_frames(buf) == [FRAME]


def test_wrong_end_byte_is_rejected():
    buf = bytearray([0x49, 0xAA, 0x07, 0x01, 0x00])
    assert extract_frames(buf) == []
