if __name__ == "__main__":
    # formats websites copied/pasted from https://ahrefs.com/top
    f = open("raw_list.txt")

    webs = []
    for l in f.readlines():
        fields = l.rstrip().split("\t")

        for field in fields:
            if "." in field and not field.endswith("M") and not field.endswith("B") and not field.endswith("K"):
                webs.append(field.rstrip())

    print(webs)
    print(len(webs))

    f = open("website_list.txt", "w")

    f.write("\n".join(webs))