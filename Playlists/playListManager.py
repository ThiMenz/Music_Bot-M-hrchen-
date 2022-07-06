def Append(appendData, filepath):
    print("playlistmanagerprint")
    with open(filepath, "a") as f:  
        f.write(appendData) 
        f.close()


def HasPermsForModifying(user, filepath):
    print("playlistmanagerprint2")
    file = open(filepath, "r")
    hasPerms = (user in file.readlines()[0])
    file.close()
    return hasPerms