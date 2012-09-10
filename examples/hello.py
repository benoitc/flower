from flower import run, schedule, tasklet

def say(s):
    for i in range(5):
        schedule()
        print(s)

def main():
    tasklet(say)("world")
    say("hello")

    run()

if __name__ == '__main__':
    main()
