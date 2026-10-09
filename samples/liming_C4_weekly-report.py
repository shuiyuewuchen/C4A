def report(tasks):
    return "\n".join(tasks)

if __name__ == "__main__":
    tasks = ["开会", "写代码", "改bug"]
    print(report(tasks))
