#!/usr/bin/env python3
# coding: utf-8

import DslamHuawei

DslamHuawei.LOGGING = True

def run_test(dslam):
    print('Платы: {}'.format(dslam.boards))
    print('Порты: {}'.format(dslam.ports))
    print('Инфо: {}'.format(dslam.get_info()))
    print('Время: {}'.format(dslam.get_time()))
    
    print('\nПрофайлы:')
    for profile in sorted(list(dslam.adsl_line_profile.keys())):
        print(profile, dslam.adsl_line_profile[profile])
    
    print('\nПрофайл 1: {}'.format(dslam.get_adsl_line_profile(1)))
    
    print('\nget_adsl_line_profile_board')
    data = dslam.get_adsl_line_profile_board(1)
    for port in range(0, dslam.ports):
        print(port, data[port])
        
    print('\nget_activated_ports:')
    print(dslam.get_activated_ports(1))
    print('\nset_adsl_line_profile_port')
    dslam.set_adsl_line_profile_port(0,0,1)
    
    print('\nget_line_operation_port:')
    for port in range(0, dslam.ports):
        print(port, dslam.get_line_operation_port(1,port))
        
    print('\nget_line_operation_board:')
    data = dslam.get_line_operation_board(1)
    for port in range(0, dslam.ports):
        print(port, data[port])
    
    print('\nget_mac_address_port:')
    for port in range(0, dslam.ports):
        print(port, dslam.get_mac_address_port(1,port))
    
    print('\nЯ жив? {}'.format(dslam.alive()))

#.boards
#.ports
#get_info(self)
#get_activated_ports(self, board)
#get_line_operation_board(self, board)
#get_line_operation_port(self, board, port)
#get_mac_address_port(self, board, port)
#get_adsl_line_profile(self, profile_index)
#get_time(self)



def main():
    dslam = DslamHuawei.DslamHuawei5600('ip', 'login', 'password')
    #dslam = DslamHuawei.DslamHuawei5616('ip', 'login', 'password')
    
    run_test(dslam)
    del dslam


if __name__ == '__main__':
    main()
