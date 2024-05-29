
import parse

def parse_syscall(raw):
    s = raw.split("(", maxsplit=1)
    name = s[0].strip()

    if len(s) == 1:
        s = raw.split("=", maxsplit=1)
        if len(s) == 1:
            return Syscall(raw, name, [], "")
        else:
            return Syscall(raw, s[0], [], s[1])
    else:
        args = s[1].strip()

    in_string = False
    num_open = 1
    index = 0
    while num_open > 0:
        if args[index] == '\\':
            index += 1 # Skip over escaped char
        elif args[index] == '"':
            in_string = not in_string
        elif not in_string:
            if args[index] == ')':
                num_open -= 1
                if num_open == 0:
                    break
            elif args[index] == '(':
                num_open += 1
        index += 1
        if index >= len(args):
            raise RuntimeError("Unmatched open parenthesis in syscall: \"{}\"".format(raw))

    ret = args[index+1:].strip()
    if ret.startswith('='):
        ret = ret[1:].strip().split(' ', maxsplit=1)[0]

    args_str = args[:index].strip()

    in_string = False
    paren = 0
    curly = 0
    sqr = 0
    index = 0
    last_end = 0
    args = []
    while index < len(args_str):
        c = args_str[index]
        if c == '\\':
           index += 1 # Skip over the escaped char
        elif c == '"':
            in_string = not in_string
        elif not in_string:
            if c == '{':
                curly += 1
            elif c == '}':
                curly -= 1
            elif c == '(':
                paren += 1
            elif c == ')':
                paren -= 1
            elif c == '[':
                sqr += 1
            elif c == ']':
                sqr -= 1
            elif c == ',':
                if curly == 0 and paren == 0 and sqr == 0:
                    arg = args_str[last_end:index]
                    args.append(arg.strip())
                    last_end = index + 1
        index += 1

    if last_end < len(args_str):
        final_arg = args_str[last_end:]
        args.append(final_arg.strip())

    #print("Parsed syscall: name={}, args={}, ret={}".format(name,args,ret))
    return Syscall(raw, name, args, ret)

class Syscall:

    def __init__(self, raw, name, args, ret):
        self.raw = raw
        self.name = name
        self.args = args
        self.ret = ret

class TracedSocket:

    def __init__(self, syscall, pid, fd, index, family, skt_type, protocol):
        self.decl = syscall
        self.pid = pid
        self.fd = fd
        self.index = index
        self.family = family
        self.ip = None
        if self.family == "AF_INET":
            self.ip = 4
        elif self.family == "AF_INET6":
            self.ip = 6
        self.skt_type = skt_type
        self.protocol = protocol 
        self.uses = []
        self.close = None
        self.bind = None
        self.connect = None
        self.tcp_data = None
        self.udp_packets = None

    def add_use(self, syscall):
        self.uses.append(syscall)


class TracedProcess:

    def __init__(self, pid, strace_lines):
        self.pid = pid
        self.syscalls = []
        for line in strace_lines:
            syscall = parse_syscall(line)
            self.syscalls.append(syscall)

    def trace_sockets(self):
        sockets = []
        next_index = {}

        def get_index(fd):
            index = 0
            if fd in next_index.keys():
                index = next_index[fd]
                next_index[fd] = index+1
            else:
                next_index[fd] = 1
            return index

        curr_sockets = {}

        def new_socket(skt):
            sockets.append(skt)
            #if skt.fd in curr_sockets.keys():
            #    print("WARNING: Concurrent Sockets with same FD: {}".format(fd))
            curr_sockets[fd] = skt

        for syscall in self.syscalls:
            if syscall.name == "socket":
                fd = int(syscall.ret)
                if len(syscall.args) != 3:
                    raise RuntimeError("socket syscall found without 3 args! {}".format(syscall.__dict__))
                f = syscall.args[0]
                t = syscall.args[1]
                p = syscall.args[2]
                skt = TracedSocket(syscall, self.pid, fd, get_index(fd),f,t,p)
                new_socket(skt)
            elif syscall.name == "socketpair":
                fd = int(syscall.ret)
                if len(syscall.args) != 4:
                    raise RuntimeError("socketpair syscall found without 4 args! {}".format(syscall.__dict__))
                f = syscall.args[0]
                t = syscall.args[1]
                p = syscall.args[2]
                pair = syscall.args[3]
                pair = parse.parse("[{},{}]",pair)
                if pair == None:
                    raise RuntimeError("Failed to parse fd pair in socketpair syscall! {}".format(syscall.__dict__))
                fd0, fd1 = pair
                skt0 = TracedSocket(syscall, self.pid, fd, get_index(fd0),f,t,p)
                new_socket(skt0)
                skt1 = TracedSocket(syscall, self.pid, fd, get_index(fd1),f,t,p)
                new_socket(skt1)
            elif syscall.name == "close":
                fd = int(syscall.args[0])
                if fd in curr_sockets.keys():
                    skt = curr_sockets[fd]
                    skt.add_use(syscall)
                    skt.close = close
                    curr_sockets.pop(fd)
            elif syscall.name == "bind":
                fd = int(syscall.args[0])
                if fd in curr_sockets.keys():
                    skt = curr_sockets[fd]
                    if skt.bind is not None:
                        raise RuntimeError("Socket was Bound mutliple times! first='{}', second = '{}'".format(skt.bind.raw,syscall.raw))
                    skt.add_use(syscall)
                    skt.bind = syscall
            elif syscall.name == "connect":
                fd = int(syscall.args[0])
                if fd in curr_sockets.keys():
                    skt = curr_sockets[fd]
                    if skt.connect is not None:
                        raise RuntimeError("Socket was connected mutliple times! first='{}', second = '{}'".format(skt.connect.raw,syscall.raw))
                    skt.add_use(syscall)
                    skt.connect = syscall
            elif syscall.name == "recv" or syscall.name == "recvfrom" or syscall.name == "recvmsg":
                fd = int(syscall.args[0])
                if fd in curr_sockets.keys():
                    skt = curr_sockets[fd]
                    skt.add_use(syscall)
            elif syscall.name == "send" or syscall.name == "sendto" or syscall.name == "sendmsg":
                fd = int(syscall.args[0])
                if fd in curr_sockets.keys():
                    skt = curr_sockets[fd]
                    skt.add_use(syscall)
        return sockets

    def trace_tcp(self, sockets):
        tcp_streams = []
        for skt in sockets:
            if skt.connect is None:
                continue
            if skt.skt_type != "SOCK_STREAM":
                continue
            if skt.ip is None:
                continue
            for use in skt.uses:
                print("TCP Use: {}".format(use.raw))

