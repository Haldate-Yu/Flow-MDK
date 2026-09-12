import numpy as np

def calcul_Q(Hu,Hd,Hb,e,n=1,b=9):
    """
    计算单个闸孔的Q
    """
    if (Hd-Hb<=0):
        Hd = Hb + 0.1
    if (Hu-Hb >2*e):
        COEF1 = 0.65
    elif ((Hu-Hb)>1.5*e) and ((Hu-Hb)<=2*e):
        COEF1 = (2.05-0.7*(Hu-Hb)/e)
    else:
        COEF1 = 1
    state = e/(Hu-Hb) #判断条件
    #print("判断条件 = ",state)
    tau_h = (Hd-Hb)/(Hu-Hb) #水深比值
    #print("水深比值 = ",tau_h)
    sigma_s = 2.31*tau_h*(1-tau_h)**0.4 #淹没系数
    #print("淹没系数 = ",sigma_s)
    u0 = 0.6-0.176*e/(Hu-Hb) #闸孔出流流量系数
    #print("闸孔出流流量系数 = ",u0)
    [zeta_k,zeta0] = np.array([0.7,0.45]) #边墩形状系数；中墩形状系数
    eps = 1-0.2*(zeta_k+(n-1)*zeta0)*(Hu-Hb)/(n*b) #侧收缩系数
    #print("侧收缩系数 = ",eps)
    m = 0.385+0.171*(2/(Hu-Hb))**0.657 #流量系数
    #print("流量系数 = ",m)
    Q = 0 #初始化
    RH = Hu-Hb
    if state <= 0.65:
        #print("COEF1 = ",COEF1)
        if (Hd-Hb <= e):
            Q = COEF1*u0*e*n*b*(2*9.81*(Hu-Hb))**0.5
        else:
            Q = COEF1*u0*e*n*b*(2*9.81*(Hu-Hd))**0.5
        # Q = sigma_s*u0*e*n*b*(2*9.81*(Hu-Hb))**0.5
    else:
        if tau_h<=0.8 :
            Q = m*eps*n*b*(2*9.81)**0.5*(Hu-Hb)**1.5
        else:
            Q = sigma_s*m*eps*n*b*(2*9.81)**0.5*(Hu-Hb)**1.5
    #print("下泄流量 = ",Q)
    return Q

def sum_Q(Hu,Hd,Hb,E):
    """
    依次计算单个闸门流量
    汇总形成全部闸门流量
    """
    sum_Q = 0
    for e in E:
        Q_single = calcul_Q(Hu,Hd,Hb,e)
        sum_Q = sum_Q + Q_single
    return sum_Q

Hu = 268.75 #上游
Hd = 267.18 #下游
Hb = 267.5 #闸门-堰顶高程
E = np.array([5,5,5,5,5]) #闸孔开度表
#n = 5 #孔数
b = 9 #单孔净宽
Q = sum_Q(Hu,Hd,Hb,E)
print("下泄流量 = ",Q)
# for Hu in range(269,285,1):
#     Q = sum_Q(Hu,Hd,Hb,E)
#     print("*****")
#     print("Hu = ",Hu)
#     print("下泄流量 = ",Q)


