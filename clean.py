from distutils.util import strtobool
import torch
import random
#序号，半径对应数组
radius = [0.26, 0.4, 0.54, 0.595, 0.765, 0.915, 0.965, 1.29, 1.54, 1.545, 2.04]

def data_clean(message_received):
    message_received = message_received.split("!")[-2]
    init_array = torch.zeros((150, 6))
    new_list = message_received.split("|")
    to_go = radius[int(new_list[0])]
    init_array[0][5]=to_go
    init_array[0][1] = 4.75
    score = int(new_list[1])
    new_new_list = new_list[2].replace("(", "").replace(")", "").split(";")
    li = random.sample(range(149),len(new_new_list)-1)
    for j in range(len(new_new_list)-1):
        new_new_new_list=new_new_list[j].split(",")
        for i in range(6):
            if i==5:
                init_array[li[j]+1][i] = radius[int(new_new_new_list[i])]
            else:
                init_array[li[j]+1][i] = float(new_new_new_list[i])
    done = strtobool(new_list[3])
    return  init_array.unsqueeze(0), score, done
