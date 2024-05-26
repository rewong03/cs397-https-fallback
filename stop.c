#include <sys/types.h>
#include <signal.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#define DEBUG

#ifdef DEBUG
#define DPRINT(fmt, ...) printf("[DEBUG] " fmt, ##__VA_ARGS__)
#else
#define DPRINT(fmt, ...)
#endif

int main(int argc, const char **argv) {
    if(argc < 2) {
        DPRINT("Usage: stop [COMMAND]\n");
        return 1;
    }
    const char *proc_name = argv[1];
    char *subproc_argv[argc];
    for(int i = 0; i < argc-1; i++) {
        subproc_argv[i] = malloc(strlen(argv[i+1]+1));
        strcpy(subproc_argv[i], argv[i+1]);
    }
    subproc_argv[argc-1] = NULL;
    
    DPRINT("Will Run Command: \"%s", proc_name);
    for(int i = 1; i < argc-1; i++) {
        DPRINT(" %s", subproc_argv[i]);
    }
    DPRINT("\" on SIGCONT...\n");

    DPRINT("Stopping...\n");

    if(kill(getpid(), SIGSTOP)) {
        perror("kill");
        return 1;
    }

    DPRINT("Resumed!\n");

    if(execvp(subproc_argv[0], subproc_argv)) {
        perror("execvp");
        return 1;
    }
    return 1;
}

