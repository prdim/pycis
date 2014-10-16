#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
pycis v.0.1, 17.10.2014
Данный скрипт предназначен для автоматизации выполнения массовых операций
на маршрутизаторах Cisco

Использование: 
./pycis.py -help - вызов данной помощи
./pycis.py -s файл_списка_хостов.txt -c файл_команд.txt

Формат списка хостов - значения, разделенные табуляцией: 
хост, юзер, пароль, пароль привелегированного режима
Пароли могут быть пустыми, тогда они будут запрошены при подключении.
Будут проигнорированы пустые строки, строки содержащие меньше 2 значений
и строки начинающиеся с '#'

Список команд - файл по одной команде в строке. 
Должен оканчиваться командой выхода.
Будут проигнорированы пустые строки, и строки начинающиеся с '#'

Copyright (c) 2014, Dmitriy Prolubnikov
Разрешается повторное распространение и использование как в виде исходного кода, 
так и в двоичной форме, с изменениями или без, при соблюдении следующих условий:
* При повторном распространении исходного кода должно оставаться указанное выше 
  уведомление об авторском праве, этот список условий и последующий отказ от гарантий.
* При повторном распространении двоичного кода должна сохраняться указанная выше 
  информация об авторском праве, этот список условий и последующий отказ от 
  гарантий в документации и/или в других материалах, поставляемых при распространении.
ЭТА ПРОГРАММА ПРЕДОСТАВЛЕНА ВЛАДЕЛЬЦАМИ АВТОРСКИХ ПРАВ И/ИЛИ ДРУГИМИ СТОРОНАМИ 
«КАК ОНА ЕСТЬ» БЕЗ КАКОГО-ЛИБО ВИДА ГАРАНТИЙ, ВЫРАЖЕННЫХ ЯВНО ИЛИ ПОДРАЗУМЕВАЕМЫХ, 
ВКЛЮЧАЯ, НО НЕ ОГРАНИЧИВАЯСЬ ИМИ, ПОДРАЗУМЕВАЕМЫЕ ГАРАНТИИ КОММЕРЧЕСКОЙ ЦЕННОСТИ 
И ПРИГОДНОСТИ ДЛЯ КОНКРЕТНОЙ ЦЕЛИ. НИ В КОЕМ СЛУЧАЕ НИ ОДИН ВЛАДЕЛЕЦ АВТОРСКИХ ПРАВ 
И НИ ОДНО ДРУГОЕ ЛИЦО, КОТОРОЕ МОЖЕТ ИЗМЕНЯТЬ И/ИЛИ ПОВТОРНО РАСПРОСТРАНЯТЬ ПРОГРАММУ, 
КАК БЫЛО СКАЗАНО ВЫШЕ, НЕ НЕСЁТ ОТВЕТСТВЕННОСТИ, ВКЛЮЧАЯ ЛЮБЫЕ ОБЩИЕ, СЛУЧАЙНЫЕ, 
СПЕЦИАЛЬНЫЕ ИЛИ ПОСЛЕДОВАВШИЕ УБЫТКИ, ВСЛЕДСТВИЕ ИСПОЛЬЗОВАНИЯ ИЛИ НЕВОЗМОЖНОСТИ 
ИСПОЛЬЗОВАНИЯ ПРОГРАММЫ (ВКЛЮЧАЯ, НО НЕ ОГРАНИЧИВАЯСЬ ПОТЕРЕЙ ДАННЫХ, ИЛИ ДАННЫМИ, 
СТАВШИМИ НЕПРАВИЛЬНЫМИ, ИЛИ ПОТЕРЯМИ ПРИНЕСЕННЫМИ ИЗ-ЗА ВАС ИЛИ ТРЕТЬИХ ЛИЦ, 
ИЛИ ОТКАЗОМ ПРОГРАММЫ РАБОТАТЬ СОВМЕСТНО С ДРУГИМИ ПРОГРАММАМИ), ДАЖЕ ЕСЛИ ТАКОЙ 
ВЛАДЕЛЕЦ ИЛИ ДРУГОЕ ЛИЦО БЫЛИ ИЗВЕЩЕНЫ О ВОЗМОЖНОСТИ ТАКИХ УБЫТКОВ.
'''

import os, sys, re, getopt, getpass
try:
    import pexpect
    import pxssh
except ImportError:
    sys.stderr.write("You do not have 'pexpect' installed.\n")
    sys.stderr.write("On Ubuntu you need the 'python-pexpect' package.\n")
    sys.stderr.write(" aptitude -y install python-pexpect\n")
    exit(1)

#
# Some constants.
#
COMMAND_PROMPT = '[#>]' ### Приглашение командного режима
TERMINAL_PROMPT = '(?i)terminal type\?'
TERMINAL_TYPE = 'vt100'
# This is the prompt we get if SSH does not have the remote host's public key stored in the cache.
SSH_NEWKEY = '(?i)are you sure you want to continue connecting'

def exit_with_usage():
    '''Вывод справки и выход
    '''
    print(globals()['__doc__'])
    os._exit(1)

def login(host, commands):
    '''Подключение к удаленному хосту и выполнение списка команд.
    
    host - список [хост,юзер,пароль1,пароль2]
    commands - список команд, должен заканчиваться командой выхода
    '''
    global COMMAND_PROMPT, TERMINAL_PROMPT, TERMINAL_TYPE, SSH_NEWKEY
    print('connect to %s' % host[0])
    password = host[2]
    if password == '':
        password = getpass.getpass('password: ')
    child = pexpect.spawn('ssh -l %s %s'%(host[1], host[0]))
    i = child.expect([pexpect.TIMEOUT, SSH_NEWKEY, COMMAND_PROMPT, '(?i)password', 'Permission denied'])
    if i == 0 or i == 4: # Timeout
        print('ERROR! could not login with SSH. Here is what SSH said:')
        print(child.before, child.after)
        print(str(child))
        return
    if i == 1: # In this case SSH does not have the public key cached.
        child.sendline ('yes')
        child.expect ('(?i)password')
    if i == 2:
        # This may happen if a public key was setup to automatically login.
        # But beware, the COMMAND_PROMPT at this point is very trivial and
        # could be fooled by some output in the MOTD or login message.
        pass
    if i == 3:
        child.sendline(password)
        child.expect ([COMMAND_PROMPT, TERMINAL_PROMPT])
    for cmd in commands:
        if cmd == 'en':
            passwordp = host[3]
            if passwordp == '':
                passwordp = getpass.getpass('Enable password: ')
            child.sendline(cmd)
            child.expect('(?i)password')
            child.sendline(passwordp)
            child.expect([pexpect.EOF, COMMAND_PROMPT, TERMINAL_PROMPT])
            print("Enable mode on")
        else:
            child.sendline (cmd)
            child.expect([pexpect.EOF, COMMAND_PROMPT, TERMINAL_PROMPT])
            print(child.before)
            
def getHosts(fileName):
    '''Чтение списка хостов из файла
    
    Значения разделены табуляцией: хост, юзер, пароль1, пароль2
    Пароли не обязательны, будут запрошены при подключении
    игнорируются пустые строки, строки на с '#' 
    и строки содержащие меньше 2 значений
    '''
    hosts = []
    h = []
    f = open(fileName)
    line = f.readline()
    while line:
        if line == '':
            pass
        elif line[0] == '#':
            pass
        else:
            h = line.split('\t')
            if len(h)<2:
                pass
            elif len(h)<3:
                h.append(['',''])
                hosts.append(h)
            elif len(h)<4:
                h.append([''])
                hosts.append(h)
            else:
                hosts.append(h[0:3])
        line = f.readline()
    f.close()
    return hosts

def getCommands(fileName):
    '''Чтение списка команд из файла
    
    Игнорируются пустые строки, и строки начинающиеся с '#'
    '''
    commands = []
    f = open(fileName)
    line = f.readline()
    while line:
        if line == '':
            pass
        elif line[0] == '#':
            pass
        else:
            commands.append(line)
        line = f.readline()
    f.close()
    return commands

def main():
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'h?s:c:', ['help','h','?'])
    except Exception as e:
        print(str(e))
        exit_with_usage()
    options = dict(optlist)
    if len(args) > 1:
        exit_with_usage()

    if [elem for elem in options if elem in ['-h','--h','-?','--?','--help']]:
        print("Help:")
        exit_with_usage()
    try:
        hostName = options['-s']
        comName = options['-c']
    except Exception as e:
        exit_with_usage()
        
    hosts = getHosts(hostName)
    commands = getCommands(comName)
    
    for host in hosts:
        login(host, commands)
        

if __name__ == '__main__':
    main()
