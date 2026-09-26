import numpy as np

from app.analysis.subjects import Box, mouth_motion
from app.planner.camera import Shot, active_person, persons_from_faces, plan_shots, shot_crop

CFG = {"close_zoom": 2.0, "medium_zoom": 1.4, "face_max": 0.45, "max_hold_s": 4.5, "min_shot_s": 1.2,
       "wide_open_s": 2.0, "wide_every_s": 20}


def two_people(talk):
    """Mặt trái (cx 0.3) và phải (cx 0.7) mỗi 0.5s; talk(t) → 0 (trái nói) / 1 (phải nói)."""
    faces = []
    for k in range(0, 80):
        t = k * 0.5
        who = talk(t)
        faces.append([t, [[0.25, 0.3, 0.1, 0.18, 0.03 if who == 0 else 0.002],
                          [0.65, 0.32, 0.1, 0.18, 0.03 if who == 1 else 0.002]]])
    return faces


def test_people_and_active_speaker():
    faces = two_people(lambda t: 0 if t < 10 else 1)
    people = persons_from_faces(faces)
    assert len(people) == 2 and people[0].cx < people[1].cx
    assert active_person(faces, people, 2, 6) == 0
    assert active_person(faces, people, 12, 16) == 1


def test_shots_cut_on_speaker_change_and_alternate():
    faces = two_people(lambda t: 0 if t < 10 else 1)
    people = persons_from_faces(faces)
    speech = [{"start": 0.5, "end": 4.0}, {"start": 4.2, "end": 9.8}, {"start": 10.0, "end": 12.0},
              {"start": 12.3, "end": 19.5}]
    shots, _ = plan_shots(0.0, 20.0, speech, faces, people, CFG, opening=True)
    assert shots[0].kind == "wide" and shots[0].end == 2.0  # mở đầu toàn cảnh
    assert shots[0].start == 0.0 and shots[-1].end == 20.0
    assert all(a.end == b.start for a, b in zip(shots, shots[1:]))  # liền mạch, không hở
    left = [s for s in shots if s.person == 0]
    right = [s for s in shots if s.person == 1]
    assert left and right
    assert min(s.start for s in right) == 10.0  # cắt sang người phải đúng lúc người đó bắt đầu nói
    assert {s.kind for s in right} >= {"close", "medium"}  # nói lâu → đổi cận ↔ trung
    assert all(s.end - s.start <= 4.5 + 1.2 + 1e-6 for s in shots)


def test_short_interjection_does_not_cut():
    faces = two_people(lambda t: 1 if 5.0 <= t < 5.5 else 0)
    people = persons_from_faces(faces)
    speech = [{"start": 0.0, "end": 4.9}, {"start": 5.0, "end": 5.5}, {"start": 5.6, "end": 9.0}]
    shots, _ = plan_shots(0.0, 9.0, speech, faces, people, CFG)
    assert all(s.person == 0 for s in shots)


def test_crop_keeps_block_ratio_and_face_in_frame():
    faces = two_people(lambda t: 0)
    people = persons_from_faces(faces)
    c = shot_crop(Shot(0, 3, "close", 0), people, "16:9", 1920, 1080, CFG)
    w, h = c.right - c.left, c.bottom - c.top
    assert abs((w * 1920) / (h * 1080) - 16 / 9) < 1e-6  # cùng tỉ lệ khối 16:9
    assert abs(w - 0.5) < 1e-6  # cận ~2 lần
    assert c.left <= people[0].cx <= c.right and c.top <= people[0].cy <= c.bottom
    wide = shot_crop(Shot(0, 3, "wide"), people, "16:9", 1920, 1080, CFG)
    assert (wide.left, wide.top, wide.right, wide.bottom) == (0.0, 0.0, 1.0, 1.0)
    med = shot_crop(Shot(0, 3, "medium", 1), people, "16:9", 1920, 1080, CFG)
    assert abs((med.right - med.left) - 1 / 1.4) < 1e-6


def test_mouth_motion_detects_change():
    a = np.zeros((100, 100), np.uint8)
    b = a.copy()
    b[70:95, 30:70] = 200  # vùng miệng thay đổi
    box = Box(x=0.2, y=0.1, w=0.6, h=0.9)
    assert mouth_motion(a, b, box) > 0.3
    assert mouth_motion(a, a, box) == 0.0


def test_merge_duplicate_face_boxes():
    from app.analysis.subjects import merge_boxes

    a = Box(x=0.2, y=0.2, w=0.2, h=0.3)
    b = Box(x=0.21, y=0.22, w=0.18, h=0.28)  # cùng mặt, cascade khác
    c = Box(x=0.7, y=0.2, w=0.15, h=0.25)
    kept = merge_boxes([b, a, c])
    assert len(kept) == 2 and a in kept and c in kept


def test_static_logo_is_not_a_person():
    faces = two_people(lambda t: 0)
    for f in faces:
        f[1].append([0.05, 0.05, 0.06, 0.08, 0.0])  # logo mặt cười đứng yên ở góc
    people = persons_from_faces(faces)
    assert len(people) == 2 and all(p.cx > 0.2 for p in people)


def test_reaction_cut_to_laughing_person():
    from app.planner.camera import merge_reactions

    # người trái nói suốt 0–12s; 6–8s có tiếng cười và người PHẢI cử động miệng (đang cười)
    faces = two_people(lambda t: 1 if 6.0 <= t < 8.0 else 0)
    people = persons_from_faces(faces)
    speech = [{"start": 0.0, "end": 12.0}]
    merged = merge_reactions(speech, [{"start": 6.0, "end": 8.0, "kind": "laugh"}])
    assert merged == [{"start": 0.0, "end": 6.0}, {"start": 6.0, "end": 8.0}, {"start": 8.0, "end": 12.0}]
    cfg = {**CFG, "max_hold_s": 3.0, "min_shot_s": 0.8}
    shots, _ = plan_shots(0.0, 12.0, merged, faces, people, cfg)
    react = [s for s in shots if s.person == 1]
    assert react and react[0].start == 6.0 and react[0].kind == "close"
    assert merge_reactions(speech, [{"start": 1, "end": 2, "kind": "shout"}]) == speech  # hét khi nói: không cắt
