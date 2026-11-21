"""Observe the installed qpos controller without changing its target/timing path."""
import time
from contextlib import contextmanager
import numpy as np

ARM = list(range(6)) + list(range(7, 13))


class EpisodeStop(Exception):
    pass


def joint_snapshot(robot):
    drive = np.asarray(robot.get_left_arm_jointState() + robot.get_right_arm_jointState(), dtype=np.float64)
    measured = np.asarray(robot.get_left_arm_real_jointState() + robot.get_right_arm_real_jointState(), dtype=np.float64)
    assert drive.shape == measured.shape == (14,) and np.isfinite(drive).all() and np.isfinite(measured).all()
    fingers = []
    for side in ('left', 'right'):
        entity = getattr(robot, side + '_entity')
        joint = getattr(robot, side + '_gripper')[0][0]
        fingers.append(float(entity.get_qpos()[entity.get_active_joints().index(joint)]))
    # The two gripper entries in *_real_jointState are still stored command values.
    return drive, measured[ARM].copy(), np.asarray(fingers)


class PlannerProbe:
    def __init__(self, original, side, events, current):
        self.original, self.side, self.events, self.current = original, side, events, current

    def __getattr__(self, name):
        return getattr(self.original, name)

    def TOPP(self, *args, **kwargs):
        event = dict(arm=self.side, action_index=self.current['action'], status='RUNNING')
        began = time.monotonic()
        try:
            value = self.original.TOPP(*args, **kwargs)
            try:
                positions = np.asarray(value[1])
                event.update(status='EMPTY' if len(positions) == 0 else 'RETURNED', steps=len(positions),
                             finite=bool(np.isfinite(positions).all()), duration=float(value[4]))
            except Exception as error:
                # Instrumentation must not turn a valid planner return into an
                # exception that the installed controller would silently swallow.
                event.update(status='OBSERVATION_ERROR',observation_error=repr(error))
            return value
        except Exception as error:
            event.update(status='EXCEPTION', error=repr(error))
            raise
        finally:
            event['seconds'] = time.monotonic() - began
            self.events.append(event)


class SceneProbe:
    def __init__(self, original, sample):
        self.original, self.sample, self.steps = original, sample, 0

    def __getattr__(self, name):
        return getattr(self.original, name)

    def step(self):
        result = self.original.step()
        self.steps += 1
        self.sample(self.steps)
        return result


@contextmanager
def observe_controller(task, sample, events, current):
    scene = task.scene
    left, right = task.robot.left_mplib_planner, task.robot.right_mplib_planner
    wrapped = SceneProbe(scene, sample)
    task.scene = wrapped
    task.robot.left_mplib_planner = PlannerProbe(left, 'left', events, current)
    task.robot.right_mplib_planner = PlannerProbe(right, 'right', events, current)
    try:
        yield wrapped
    finally:
        task.scene = scene
        task.robot.left_mplib_planner, task.robot.right_mplib_planner = left, right


def contact_sample(scene, gripper_names, bottle_name):
    records = []
    for contact in scene.get_contacts():
        bodies = [str(body.entity.name) for body in contact.bodies]
        impulses = [float(np.linalg.norm(point.impulse)) for point in contact.points]
        if not impulses or max(impulses) <= 1e-8:
            continue
        left = any(name.startswith('fl_') for name in bodies)
        right = any(name.startswith('fr_') for name in bodies)
        records.append(dict(bodies=bodies, max_impulse=max(impulses),
            robot_table=any('table' in name.lower() for name in bodies) and (left or right),
            cross_arm=left and right,
            gripper_bottle=bottle_name in bodies and any(name in gripper_names for name in bodies)))
    return records


def telemetry_summary(rows, events):
    if not rows:
        return dict(samples=0, topp_calls=len(events))
    measured=np.asarray([row['measured_arm'] for row in rows]);drive=np.asarray([row['drive'][ARM] for row in rows])
    tracking=np.rad2deg(measured-drive)
    return dict(samples=len(rows), drive_vs_measured_arm_rmse_degrees=float(np.sqrt(np.mean(tracking**2))),
        drive_vs_measured_arm_max_degrees=float(abs(tracking).max()),
        topp_calls=len(events),topp_exceptions=sum(e['status']=='EXCEPTION' for e in events),
        topp_empty_results=sum(e['status']=='EMPTY' for e in events),
        robot_table_contact_samples=sum(any(c['robot_table'] for c in row['contacts']) for row in rows),
        cross_arm_contact_samples=sum(any(c['cross_arm'] for c in row['contacts']) for row in rows),
        gripper_bottle_contact_samples=sum(any(c['gripper_bottle'] for c in row['contacts']) for row in rows),
        maximum_bottle_height=float(max(row['bottle'][2] for row in rows)))
