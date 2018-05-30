# coding: utf8

import pexpect
import datetime
import time
import re
import os

LOGGING = False

class DslamHuawei():
    
    @staticmethod
    def check_out(command, str_out):
        """ Проверка вывода команды """
        bad_strings = ('Failure: System is busy', 'please wait',  'Unknown command')
        if command not in str_out:
            return False
        for string in bad_strings:
            if string in str_out:
                return False
        return True    

    def __init__(self, ip, login, password,  timeout):
        self.ip = ip
        self.connect(login,  password,  timeout)

        # Распознавание версии ПО
        str_out = self.write_read_data('display version')
        self.version = re.search(r'\b(MA.+?)\b', str_out).group(1)
        self.set_adsl_line_profile()
    
    def __del__(self):
        self.tn.close()
    
    def connect(self, login, password,  timeout):
        """ Подключиться к DSLAM """
        self.tn = pexpect.spawn('telnet {}'.format(self.ip))
        self.tn.expect('>>User name:')
        self.tn.sendline(login)
        self.tn.expect('>>User password:')
        self.tn.sendline(password)
        self.tn.expect('(>|\) ----)')
        self.tn.sendline(' ')
        self.tn.expect('>')
        commands = ['enable',
                    'idle-timeout {}'.format(timeout),
                    'scroll 512',
                    'undo smart',
                    'undo interactive',
                    'undo alarm output all',
                    'config',
                    'undo info-center enable',
                    'quit']
        for command in commands:
            self.tn.sendline(command)
            self.tn.expect('#')
        # Распознавание hostname
        self.hostname = re.search('([\w-]+)$', self.tn.before.decode('utf-8')).group(1)
    
    def logging(self,  in_out, line):
        if not os.path.exists('dslam_logs'):
            os.mkdir('dslam_logs')
        with open('dslam_logs{}{} {}.txt'.format(os.sep, self.ip,  datetime.datetime.now().strftime('%d-%m-%y')), 'a') as log_file:
            log_file.write('{} {}\n{}\n**************************************\n'.format(in_out,  datetime.datetime.now().strftime('%H:%M:%S'),  line))
        
    def alive(self):
        """ Проверка есть ли связь с DSLAM """
        str_out = self.write_read_data('',  short=True)
        if str_out == '\n':
            return True
        elif str_out is False:
            return False
    
    def write_data(self, command):
        """ Отправка команды """
        command_line = command
        if LOGGING:
            self.logging('in',  command_line)
        self.tn.sendline(command_line)
        return True

    def read_data(self, command,  short):
        """ Чтение данных """
        command_line = command
        result = ''
        while True:
            try:
                self.tn.expect('.{}.*#'.format(self.hostname), timeout=30)
            except Exception as ex:
                print('{}: ошибка чтения. Команда - {}'.format(self.hostname, command_line))
                print(str(ex).split('\n')[0])
                return False
            result += re.sub(r'[^A-Za-z0-9\n\./: _-]|(.\x1b\[..)', '', self.tn.before.decode('utf-8'))
            if LOGGING:
                self.logging('out',  result)
            if result.count('\n') == 1 and not short:
                continue
            if self.check_out(command_line, result):
                #if LOGGING:
                    #self.logging('out',  result)                
                return result
            else:
                time.sleep(15)
                while True:
                    try:
                        self.tn.expect('#', timeout=1)
                    except:
                        break
                return -1                  
        
    def write_read_data(self, command,  short=False):
        """ Выполнение команды и получение результата """
        command_line = command
        for count in range(0, 5):
            self.write_data(command_line)
            result = self.read_data(command_line,  short)
            if (result != -1) and (result is not False):
                return result
        return False

    def set_boards(self, boards_list):
        """ Установить self.boards - список плат """
        self.boards = []
        for board in boards_list:
            command_line = 'display version 0/{}'.format(board)
            str_out = self.write_read_data(command_line)
            if str_out is False:
                return False
            if 'Failure' not in str_out:
                self.boards.append(board) 
    
    def set_adsl_line_profile(self):
        """ Установить self.adsl_line_profile - список профайлов линий """
        command_line = 'display adsl line-profile'
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False
        self.adsl_line_profile = {}
        prev_name = ''
        prev_index = ''
        prev_up_rate = ''
        prev_dw_rate = ''
        for line in str_out.split('\n'):
            current_index = line[0:10].strip()
            current_name = line[10:21].strip()
            current_dw_rate = line[54:65].strip()
            current_up_rate = line[74:80].strip()
            try:
                int(current_index)
            except:
                if prev_index == '':
                    continue
                if current_name == '-----------':
                    self.adsl_line_profile[int(prev_index)] = {'profile_name' : prev_name, 'dw_rate': prev_dw_rate, 'up_rate' : prev_up_rate}
                    break
                prev_name += current_name
                continue
            if prev_index != '' and prev_name != '':
                self.adsl_line_profile[int(prev_index)] = {'profile_name' : prev_name, 'dw_rate': prev_dw_rate, 'up_rate' : prev_up_rate}
            prev_index = current_index
            prev_name = current_name
            prev_dw_rate = current_dw_rate
            prev_up_rate = current_up_rate
    
    def get_info(self):
        """ Получить информацию о DSLAM """
        return {'ip' : self.ip,
                'hostname' : self.hostname,
                'version' : self.version,
                'model' : self.model}
    
    def get_activated_ports(self, board):
        """ Получить список активированных портов с платы """
        if board not in self.boards:
            return []
        regex = re.compile(r' +(\w*) +ADSL +Activated')
        command_line = 'display board 0/{}'.format(board)
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False
        result = []
        for line in str_out.split('\n'):
            try:
                result.append(int(regex.search(line).group(1)))
            except:
                continue
        return result       
    
    def get_line_operation_board(self, board):
        """ Получить список параметров линий с активированных портов """
        command = 'display line operation board'
        template = {'up_snr' : '-',
                    'dw_snr' : '-',
                    'up_att' : '-',
                    'dw_att' : '-',
                    'max_up_rate' : '-',
                    'max_dw_rate' : '-',
                    'up_rate' : '-',
                    'dw_rate' : '-'}
        result = [template for x in range(0, self.ports)]
        regex = r"( +-?\d+\.?\d*){11}"
        command_line = '{} 0/{}'.format(command, board)
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False        
        matches = re.finditer(regex, str_out)
        for match in matches:
            match_list = list(match.group(0).split())
            result[int(match_list[0])] = {'up_snr' : float(match_list[1]),
                                          'dw_snr' : float(match_list[2]),
                                          'up_att' : float(match_list[3]),
                                          'dw_att' : float(match_list[4]),
                                          'max_up_rate' : float(match_list[5]),
                                          'max_dw_rate' : float(match_list[6]),
                                          'up_rate' : float(match_list[9]),
                                          'dw_rate' : float(match_list[10])}
        return result        
    
    def get_line_operation_port(self, board, port):
        """ Получить параметры линии с порта """
        command = 'display line operation port'
        command_line = '{} 0/{}/{}'.format(command, board, port)
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False
        if re.search(r'Failure:.+is not activ(e|ated)', str_out):
            return {}
        dw_rate = float(re.search(r'Downstream (channel|actual).+rate.+: (\d+)', str_out).group(2))
        max_dw_rate = float(re.search(r'Downstream max.+: (\d+)', str_out).group(1))
        dw_snr = float(re.search(r'Downstream channel SNR.+: (.+)', str_out).group(1))
        dw_att = float(re.search(r'Downstream channel attenuation.+: (.+)', str_out).group(1))
        up_rate = float(re.search(r'Upstream (channel|actual).+rate.+: (\d+)', str_out).group(2))
        max_up_rate = float(re.search(r'Upstream max.+: (\d+)', str_out).group(1))
        up_snr = float(re.search(r'Upstream channel SNR.+: (.+)', str_out).group(1))
        up_att = float(re.search(r'Upstream channel attenuation.+: (.+)', str_out).group(1))
        return {'dw_rate' : dw_rate,
                'max_dw_rate' : max_dw_rate,
                'dw_snr' : dw_snr,
                'dw_att' : dw_att,
                'up_rate' : up_rate,
                'max_up_rate' : max_up_rate,
                'up_snr' : up_snr,
                'up_att' : up_att}
    
    def get_mac_address_port(self, board, port):
        """ Получить список MAC-адресов с порта """
        result = []
        regex = r"\b([0-9a-f-]{14})\b.*\b(\d+)"
        command = 'display mac-address port'
        command_line = '{} 0/{}/{}'.format(command, board,  port)
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False
        if 'Failure:' in str_out:
            return []
        elif 'Total:' in str_out:
            matches = re.finditer(regex, str_out)
            for match in matches:
                result.append((match.group(1), match.group(2)))
            return result
    
    def get_adsl_line_profile(self, profile_index):
        """ Получить описание профайла линии по его индексу """
        if profile_index not in self.adsl_line_profile:
            return 'The profile does not exist'
        command = 'display adsl line-profile'
        command_line = '{} {}'.format(command, profile_index)
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False
        result = ''
        for line in str_out.split('\n'):
            if len(line) < 1:
                continue
            if line[0] == ' ' and line[3] != '-':
                result += (line + '\n')
        return result
    
    def get_adsl_line_profile_board(self, board):
        """ Получить список активированных портов с платы """
        if board not in self.boards:
            return []
        regex = re.compile(r' +(\w*) +ADSL +Activat(ed|ing) +(\w*)')
        command_line = 'display board 0/{}'.format(board)
        str_out = self.write_read_data(command_line)
        if str_out is False:
            return False
        result = []
        for line in str_out.split('\n'):
            try:
                result.append(int(regex.search(line).group(3)))
            except:
                continue
        return result       

    def get_time(self):
        """ Получить Дату - Время с DSLAM """
        command = 'display time'
        str_out = self.write_read_data(command)
        if str_out is False:
            return False
        list_date = re.search(r'(\w{4}-\w{2}-\w{2})', str_out).group(1).split('-')
        list_time = re.search(r'(\w{2}:\w{2}:\w{2})', str_out).group(1).split(':')
        return datetime.datetime(int(list_date[0]), int(list_date[1]), int(list_date[2]), int(list_time[0]), int(list_time[1]), int(list_time[2]))
    
    def set_activate_port(self, board, port):
        """ Активировать порт """
        if (board not in self.boards) or (port not in range(0, self.ports)):
            return False        
        self.write_read_data('config',  short=True)
        self.write_read_data('interface adsl 0/{}'.format(board),  short=True)
        self.write_read_data('activate {}'.format(port))
        self.write_read_data('quit',  short=True)
        self.write_read_data('quit',  short=True)
    
    def set_deactivate_port(self, board, port):
        """ Деактивировать порт """
        if (board not in self.boards) or (port not in range(0, self.ports)):
            return False         
        self.write_read_data('config',  short=True)
        self.write_read_data('interface adsl 0/{}'.format(board),  short=True)
        self.write_read_data('deactivate {}'.format(port))
        self.write_read_data('quit',  short=True)
        self.write_read_data('quit',  short=True)
        
    def set_adsl_line_profile_port(self, board, port, profile_index):
        """ Изменить профайл на порту """
        if (board not in self.boards) or (port not in range(0, self.ports)):
            return False         
        if profile_index not in self.adsl_line_profile:
            return False  
        self.write_read_data('config',  short=True)
        self.write_read_data('interface adsl 0/{}'.format(board),  short=True)
        self.write_read_data('deactivate {}'.format(port))
        self.write_read_data('activate {} profile-index {}'.format(port, profile_index))
        self.write_read_data('quit',  short=True)
        self.write_read_data('quit',  short=True)
        
    def execute_command(self, command, short=False):
        command_line = command.strip()
        str_out = self.write_read_data(command, short)
        if str_out is False:
            return False
        return str_out


class DslamHuawei5600(DslamHuawei):
    """ Huawei MA5600 """
    def __init__(self, ip, login, password, timeout=30):
        super().__init__(ip, login, password,  timeout)
        self.ports = 64
        self.model = '5600'
        self.set_boards()
    
    def set_boards(self):
        boards_list =  [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15]
        super().set_boards(boards_list)

            

class DslamHuawei5616(DslamHuawei):
    """ Huawei MA5616 """
    def __init__(self, ip, login, password,  timeout=30):
        super().__init__(ip, login, password,  timeout)
        self.ports = 32
        self.model = '5616'
        self.set_boards()
    
    def set_boards(self):
        boards_list =  [1, 2, 3, 4]
        super().set_boards(boards_list)

