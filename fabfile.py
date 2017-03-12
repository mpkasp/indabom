from fabric.api import *
from fabric.operations import local
from fabric.contrib.console import confirm
from time import localtime
import calendar
import fabric
import os

"""
Restarting is annoying because supervisord requires root to run start/stop :/
Everything else uses the unprivileged indabom user
"""

indabom_servers = {
    '35.184.50.52' : {'type': ['prod', 'all', ]},
}

def help():
    print "usage: fab [dev|prod][:user] [deploy|restart|test|test_failfast|reqs_install|pip_install|migrate]"

def prod(user='indabom'):
    env.hosts = ['{0}@{1}'.format(user, h) for h in indabom_servers if 'prod' in indabom_servers[h]['type']]

def all():
    env.hosts = ['root@{0}'.format(h) for h in indabom_servers if 'all' in indabom_servers[h]['type']]

def update_time():
    run('ntpdate pool.ntp.org')

def deploy():
    branch = 'master'
    with cd('/home/indabom/web/site'):
        run('git checkout {0}'.format(branch))
        run('git pull')

def test():
    with cd('/home/indabom/web/site/src'):
        run('source /home/indabom/web/bin/activate && python -Wi /home/indabom/web/site/src/manage.py test --noinput')

def test_failfast():
    with cd('/home/indabom/web/site/src'):
        run('source /home/indabom/web/bin/activate && python -Wi /home/indabom/web/site/src/manage.py test --failfast --noinput')

def migrate():
    """
    Runs all migrations across all indabom apps
    """
    run('source /home/indabom/web/bin/activate && /home/indabom/web/site/src/manage.py migrate')

def migrate_fake():
    """
    Runs all migrations across all indabom apps
    """
    run('source /home/indabom/web/bin/activate && /home/indabom/web/site/src/manage.py migrate --fake')

def restart_web():
    """
    Needs to be run as root (see prod:user=root) because supervisorctl must be called as root :/ annoying
    """
    run('supervisorctl restart indabom')

def install_supervisor():
    """
    Needs to be run as root (see prod:user=root) because supervisorctl must be called as root :/ annoying
    """
    run('rm -f /etc/supervisor/conf.d/*.conf')
    run('cp /home/indabom/web/site/scripts/supervisord/*.conf /etc/supervisor/conf.d/')

    run('supervisorctl reread')
    run('supervisorctl update')

def supervisor_status():
    """
    Needs to be run as root (see prod:user=root) because supervisorctl must be called as root :/ annoying
    """
    run('supervisorctl status')

def mkdirs():
    """
    Needs to be run as root (see prod:user=root) because supervisorctl must be called as root :/ annoying
    """
    the_dirs = ['/var/log/indabom', '/home/indabom/web', '/var/run/indabom', ]

    for d in the_dirs:
        if fabric.contrib.files.exists(d):
            continue

        run('mkdir -p {}'.format(d))
        run('chown -R indabom:indabom {}'.format(d))

def make_virtualenv():
    if fabric.contrib.files.exists('/home/indabom/web/bin'):
        return

    run('virtualenv /home/indabom/web/')

    run('chown -R indabom:indabom /home/indabom/web/')

def clone_web_repo():
    if fabric.contrib.files.exists('/home/indabom/web/site'):
        return

    sudo('git clone https://github.com/mpkasp/indabom.git /home/indabom/web/site', user='indabom')

def pip_install():
    run('source /home/indabom/web/bin/activate && pip install -r /home/indabom/web/site/requirements.txt')

def install_reqs():
    run('apt-get update')
    run('apt-get -y install libmysqlclient-dev supervisor python-virtualenv git python-pip python-dev libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev nginx')

def install_newnginx():
    """
    Needs to be run as root
    """

    run('curl http://nginx.org/keys/nginx_signing.key | apt-key add -')
    run('echo -e "deb http://nginx.org/packages/mainline/ubuntu/ `lsb_release -cs` nginx\ndeb-src http://nginx.org/packages/mainline/ubuntu/ `lsb_release -cs` nginx" > /etc/apt/sources.list.d/nginx.list')
    run('apt-get update')
    run('apt-get remove nginx-core')
    run('apt-get remove nginx-common')
    run('apt-get purge nginx')
    run('apt-get install nginx')

def install_nginx_config():
    """
    Needs to be run as root
    """

    run('rm -f /etc/nginx/conf.d/*')
    run('cp -f /home/indabom/web/site/scripts/nginx/indabom-config /etc/nginx/conf.d/indabom.conf')
    run('service nginx configtest')
    run('service nginx reload')

def user_exists(user):
    """
    Determine if a user exists with given user.

    This returns the information as a dictionary
    '{"name":<str>,"uid":<str>,"gid":<str>,"home":<str>,"shell":<str>}' or 'None'
    if the user does not exist.
    """
    with fabric.api.settings(fabric.api.hide('warnings','stderr','stdout','running'), warn_only=True):
        user_data = fabric.api.run("cat /etc/passwd | egrep '^%s:' ; true" % user)

    if user_data:
        u = user_data.split(":")
        return dict(name=u[0],uid=u[2],gid=u[3],home=u[5],shell=u[6])
    else:
        return None

def group_exists(name):
    """
    Determine if a group exists with a given name.

    This returns the information as a dictionary
    '{"name":<str>,"gid":<str>,"members":<list[str]>}' or 'None'
    if the group does not exist.
    """
    with fabric.api.settings(fabric.api.hide('warnings','stderr','stdout','running'),warn_only=True):
        group_data = fabric.api.run("cat /etc/group | egrep '^%s:' ; true" % (name))

    if group_data:
        name,_,gid,members = group_data.split(":",4)
        return dict(name=name,gid=gid,members=tuple(m.strip() for m in members.split(",")))
    else:
        return None

def ssh_keygen(username):
    """ Generates a pair of DSA keys in the user's home .ssh directory."""
    d = user_exists(username)
    assert d, fabric.colors.red("User does not exist: %s" % username)

    home = d['home']
    if not fabric.contrib.files.exists(os.path.join(home, ".ssh/id_rsa.pub")):
        fabric.api.run("mkdir -p %s" % os.path.join(home, ".ssh/"))
        fabric.api.run("ssh-keygen -q -t rsa -f '%s' -N ''" % os.path.join(home,'.ssh/id_rsa'))
        run('chown indabom:indabom {}'.format("/home/indabom/.ssh"))
        run('chown indabom:indabom {}'.format("/home/indabom/.ssh/id_rsa"))
        run('chown indabom:indabom {}'.format("/home/indabom/.ssh/id_rsa.pub"))

def add_indabom_user():
    if group_exists('indabom') is None:
        run('groupadd indabom')

    if user_exists('indabom') is None:
        run('useradd indabom -s /bin/bash -m -g indabom')

    if fabric.contrib.files.exists('/home/indabom/.ssh/id_dsa.pub') == False:
        ssh_keygen('indabom')

def make_web_server():
    update_time()

    add_indabom_user()
    install_reqs()
    mkdirs()
    make_virtualenv()

    run('cat /home/indabom/.ssh/id_rsa.pub')

    if confirm('Have you added the above public key to github\'s deployment keys?', default=False) == False:
        return

    clone_web_repo()
    pip_install()

    #install_newnginx() # TODO: why?
    #install_nginx_config() # TODO: generate nginx config
    install_supervisor()

    # todo: mount for image uploads
    # todo: stock local_settings.py maybe?

    #print "Don't forget to GRANT INSERT, SELECT, UPDATE, CREATE, DELETE, INDEX ON indabom.* TO 'dbclient'@'[new server local name]' IDENTIFIED BY '[password]'"
