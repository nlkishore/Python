from configparser import ConfigParser


def readConfigValue(section,tkey):
    parser = ConfigParser()
    parser.read("file.ini")
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

print(readConfigValue('wiki','username'))