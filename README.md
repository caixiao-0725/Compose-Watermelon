# Compose-Watermelon
ai 合成大西瓜
## 大致思路：
1.unity传输来的数据包含了每个水果瞬时的{[(position_x,position_y),(velocity_x,velocity_y),angulor,angulor_speed],score}，假设水果的数量不超过150个，所以先定义了shape为[150,6]的tensor，初始化所有的值为0，然后将所有的水果的数据放入tensor(这里我打乱了水果的顺序，这样tensor的靠后的几行也能得到有效的训练)，数据清洗放在了clean.py中。
<br/>
2.agent选择的是dqn网络，model采取 resnet50进行训练。  
<br/>

