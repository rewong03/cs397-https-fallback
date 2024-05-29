
import subprocess as subproc
import atexit

 
class NetDev:

    REGISTERED = {}

    def close_all():
        for name,dev in NetDev.REGISTERED.items():
            if not dev.closed:
                dev.close()

    def run_qdisc_cmd(self, cmd_type="change"):
        cmd = ["sudo", "tc", "qdisc", cmd_type, "dev", self.name, self.parent, "netem"]
        cmd.extend(["loss", "{}%".format(self.loss_percent)])
        cmd.extend(["delay", "{}ms".format(self.delay_ms)])
        cp = subproc.run(cmd)
        if cp.returncode != 0:
            raise RuntimeError("Command: {} exited with code ({})".format(cmd,cp.returncode))

    def __init__(self, dev_name, parent="root"):
        # Name of the device "eth0", "wlp1n0", etc.
        self.name = dev_name
        # qdisc parent name
        self.parent = parent

        # Current emulated network conditions
        self.loss_percent = 0
        self.delay_ms = 0
        self.closed = True

        if self.name in NetDev.REGISTERED:
            raise RuntimeError("Trying to register NetDev {} twice!".format(self.name))
        else:
            self.run_qdisc_cmd(cmd_type="add")
            NetDev.REGISTERED[self.name] = self
            self.closed = False

    def close(self):
        if self.closed:
            raise RuntimeError("Trying to close NetDev which is already closed!")
        cp = subproc.run(["sudo", "tc", "qdisc", "del", "dev", self.name, self.parent])
        if cp.returncode != 0:
            raise RuntimeError('Could not reset NetDev conditions for device "{}"!'.format(self.name))
        else:
            self.closed = True

    def set_delay(self, delay_ms):
        self.delay_ms = delay_ms

    def set_loss(self, loss_percent):
        self.loss_percent = loss_percent

    def update(self):
        self.run_qdisc_cmd(cmd_type="change")

atexit.register(NetDev.close_all)

