from configparser import ConfigParser


def readConfigValue(section,tkey):
    parser = ConfigParser()
    parser.read("/Users/yaswitha/k8s/python/Python/Python/ConfigReader/file.ini")
    tvalue=''
    for element in parser.sections():
        if (section==element):
            #print ('Section:', element)
            #print ('  Options:', parser.options(element))
            for name, value in parser.items(element):
                if(tkey==name):
                    #print ('  %s = %s' % (name, value))
                    tvalue=value
            #print
    return tvalue

print(f"{readConfigValue('wiki','username')}")