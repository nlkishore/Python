#open file in read mode
file = open("/Users/yaswitha/k8s/python/Python/Python/ProfessionalSummary_v02.txt", "r")

#read the content of file
data = file.read()

#get the length of the data
number_of_characters = len(data)

print('Number of characters in text file :', number_of_characters)