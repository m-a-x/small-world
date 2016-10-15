from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import easygui as eGUI
import csv


def get_login_data():
    '''
    prompts user for their facebook login information
    '''
    email = eGUI.enterbox(msg='Please enter your facebook email:', title='Find Weird Connections')
    pword = eGUI.passwordbox(msg='Please enter your password:', title='Sending to Max')
    return (email, pword)
    
    
def login(driver, email, pword):
    '''
    logs in to facebook mobile login pages
    '''
    un = driver.find_element_by_name('email')
    pw = driver.find_element_by_name('pass')
    un.send_keys(email)
    pw.send_keys(pword)
    pw.submit()


def trim_link(datum):
    '''
    extracts f_id from url to someones profile
    '''
    f_id = datum.get_attribute('href')[:-12]
    f_id = f_id[23:]
    return f_id


def write_f_ids(f_id_dic):
    '''
    writes your frinds ids to a csv file
    '''
    with open('f_id.csv', 'w') as datafile:
        df = csv.writer(datafile)
        for name, f_id in f_id_dic.iteritems():
            df.writerow([f_id] + [name])


def read_f_ids():
    '''
    reads f_id.csv into a dictionary - keys are ids, values are friend names
    basically just to save progress to skip running the mutuals alg erry time
    '''
    with open('f_id.csv', 'r') as datafile:
        df = csv.reader(datafile)
        f_id_dic = {rows[0]:rows[1] for rows in df}
    return f_id_dic
    

def write_mutuals(mutuals_dic):
    '''
    writes data scraped using get_all_mutuals to csv to save progress
    '''
    with open('mutuals.csv', 'w') as datafile:
        df = csv.writer(datafile)
        for f_id, m_ids in mutuals_dic.iteritems():
            df.writerow([f_id] + m_ids)


def read_mutuals():
    '''
    reads mutuals.csv into a dictionary (same format from which it was written)
    basically just to save progress to skip running the mutuals alg erry time
    '''
    with open('mutuals.csv', 'r') as datafile:
        df = csv.reader(datafile)
        mutuals_dic = {rows[0]:rows[1:] for rows in df}
    return mutuals_dic


def get_f_ids(your_fb_id):
    '''
    initiates the gathering of your facebook friends' ids by calling scrape_f_id
    '''
    (email, pword) = get_login_data()
    driver = webdriver.Firefox()
    driver.get("https://m.facebook.com/" + your_fb_id + "/friends?all=1&startindex=0")
    login(driver, email, pword)
    f_id_dic = scrape_f_ids(driver)
    driver.close()
    return f_id_dic
    

def scrape_f_ids(driver):
    '''
    does the heavy lifting of scraping for your friends ids
    the html classnames may not be the same as yours 
    '''
    f_id_dic = {}
    first_run = True
    while True:# the first page has different classnames for some reason
        if first_run: # classname was cc for me, cd for my brother
            usernames = driver.find_elements_by_class_name('cc')
            first_run = False 
        else:
            usernames = driver.find_elements_by_class_name('bo') # this was bo for me, bp for my brother
        for datum in usernames:
            f_id = trim_link(datum)
            f_id_dic[str(datum.text.encode('utf-8').decode('ascii','ignore'))] = f_id
        try:
            get_next_page(driver, 'm_more_friends')
        except NoSuchElementException:
            break
    return f_id_dic


def get_mutual_page_data(mutuals, driver, cn):
    '''
    gets the f_ids of a single 'mutual friends' page 
    '''
    u_link = driver.find_elements_by_class_name(cn)
    for datum in u_link:
        try:
            f_id = trim_link(datum)
            mutuals.append(f_id)
        except TypeError:
            break


def get_next_page(driver, next_page_element):
    '''
    when scrolling through pages of your friends or your mutual friends,
    get_next_page finds the "next page element" i.e. m_more_friends or 
    m_more_mutual_friends (on browser, hyperlinked '24 More Friends') and clicks it
    '''
    next_page = driver.find_element_by_id(next_page_element)
    next_url = next_page.find_element_by_tag_name('a').get_attribute('href')
    driver.get(next_url)

   
def get_mutuals(f_id, driver):
    '''
    gets the mutual friends (ids) between you and f_id in a list
    '''
    mutuals = []
    url = 'https://m.facebook.com/'+ f_id + '/friends?mutual=1&startindex=0'
    driver.get(url)
    while True:
        get_mutual_page_data(mutuals, driver, "bm")
        if len(mutuals) == 0:
            get_mutual_page_data(mutuals, driver, "bn")
        try:
            get_next_page(driver, 'm_more_mutual_friends')
        except NoSuchElementException:
            break
    return mutuals
    
def get_all_mutuals(id_list):
    '''
    gets all of the mutual friends (ids) between you and your entire friend list
    in a dictionary. TAKES ABOUT 4-5 MINUTES per 100 friends
    '''
    (email, pword) = get_login_data()
    driver = webdriver.Firefox()
    url = 'https://m.facebook.com/'+ id_list[0] + '/friends?mutual=1&startindex=0'
    driver.get(url)
    login(driver, email, pword)
    mutuals_dic = {}
    i = 1.0
    for f_id in id_list:
        print "About " + str(i/len(id_list)*100) + "% done getting all mutuals."
        i += 1.0
        mutuals_dic[f_id] = get_mutuals(f_id, driver)
    driver.close()
    return mutuals_dic


def get_weird_cnxn(m_dic, id_dic):
    '''
    very rough version of finding weird connections between people
    basically counts the overlap of your mutuals with a friend and your mutuals
    with each of your friends mutuals, easy to think about like a venn diagram.
    
    ONLY like 1/15 of these are interesting/unexpected, but still it works.
    '''
    possibly_weird = []
    for f_id in m_dic.keys():
        mutuals_of_f = m_dic[f_id]
        for mutual in mutuals_of_f:
            try:
                mutuals_of_mutual = m_dic[mutual]
            except KeyError:
                continue
            acquaintences = set(mutuals_of_f) & set(mutuals_of_mutual)
            evidence_acquainted = len(acquaintences)
            if evidence_acquainted <= 1 and (f_id[:7] != 'profile') and (mutual[:7] != 'profile'): # most people have changed their urls but this doesn't work for people who havent 
                if (id_dic[mutual], id_dic[f_id]) not in possibly_weird:
                    possibly_weird.append((id_dic[f_id], id_dic[mutual]))
                    if mutual == 'caleb.alan':
                        print mutuals_of_f
                        print f_id
                        print mutuals_of_mutual                        
                        print acquaintences
                        
    return possibly_weird

if __name__=='__main__':
    f_id_dic = get_f_ids('maxmatti0li') #your id here, takes about a minute
    write_f_ids(f_id_dic)
    
    id_dic = read_f_ids()
    id_list = id_dic.keys()
    
    mutuals_dic = get_all_mutuals(id_list) # takes about 4-5 minutes per 100 friends you have
    write_mutuals(mutuals_dic)
    
    m_dic = read_mutuals()
    wl = get_weird_cnxn(m_dic, id_dic) 
