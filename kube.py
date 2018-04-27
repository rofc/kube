#!/usr/bin/python3

import argparse
import shlex, subprocess

parser = argparse.ArgumentParser(description='K8S all-in-one')
parser.add_argument('-a', '--app', help='Options: alice|b2b|bob|fulfillment|putaway|reception|statusnotifier|tms|transport|wms',default='alice')
parser.add_argument('-c', '--command', help='Options: fullimport|migrate',default='test')
parser.add_argument('-n', '--namespace', help='Options: production|sandbox|staging',default='sandbox')
args = parser.parse_args()

app = args.app
command = args.command
namespace= args.namespace

def getPod(namespace, app):
    myPod = subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl get pods --namespace=' + namespace + '|egrep -i ^' + app + '|grep Running |tail -n1 |awk \'{print $1}\''], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
    return myPod

def getPods(namespace, app):
    pods = subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl get pods --namespace=' + namespace + '|grep -i ' + app + '|grep Running |awk \'{print $1}\''], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
    return pods

def restartConsumers(namespace, app):
    workers = app + "-workers"
    pods = getPods(namespace, workers)
    pod = str.splitlines(pods)
    for i in range(len(pod)):
      print("Restarteando pod \"" + pod[i] + "\" en " + namespace)
      subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl delete pod --namespace=' + namespace + ' ' + pod[i]])

def runFullImport(namespace):
    pod = getPod(namespace, 'bob-workers-fullimport-initiator')
    if namespace == 'production':
        env = 'live'
    else:
        env = 'testing'
    print("Running fullimport in " + pod + " (" + namespace + ")")
    print("[[ LOGS ]] BOB FullImport Worker: kubectl logs -c php -f " + pod + " --namespace=" + namespace)
    print("[[ LOGS ]] BOB Solr Worker: kubectl logs -c php -f " + getPod(namespace, 'bob-workers-solr') + " --namespace=" + namespace)
    print("[[ LOGS ]] Solr: kubectl logs -c php -f " + getPod(namespace, 'solr') + " --namespace=" + namespace)
    subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl exec --namespace=' + namespace + ' -ti -c php ' + pod + ' -- php console rocket-queue:full-import --env=' + env])

def runMigrations(namespace, app):
    pod = getPod(namespace, app + "-web")
    print("Running migration in " + pod + " (" + namespace + ")")
    if app == 'bob':
      subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl exec --namespace=' + namespace + ' -ti -c fpm ' + pod + ' -- php -d memory_limit=4G bob/cli/index.php --env=testing --module=maintenance --controller=schema-updater --action=index'])
    else:
      subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl exec --namespace=' + namespace + ' -ti -c fpm ' + pod + ' -- php artisan migrate'])

def fixDatabase(namespace):
    for i in range(0,2):
        pod = "mysql-" +str(i)
        print("Ejecutando 'mysqladmin flush-hosts' en " + pod)
        subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl exec --namespace=' + namespace + ' -ti -c mysql ' + pod  + ' -- mysqladmin flush-hosts'])
        print("Ejecutando 'mysql -e \'SET GLOBAL max_connect_errors=10000000;\'' en " + pod)
        subprocess.run(['/bin/bash', '-c', '/usr/bin/kubectl exec --namespace=' + namespace + ' -ti -c mysql ' + pod + ' -- mysql -e \'SET GLOBAL max_connect_errors=10000000;\''])
    print("Tareas finalizadas")

if command == 'fullimport':
    runFullImport(namespace)
elif command == 'getpods':
    getPods(namespace, app)
elif command == 'migrate':
    runMigrations(namespace, app)
elif command == 'fixdb':
    fixDatabase(namespace)
elif command == 'restart-consumers':
    restartConsumers(namespace, app)
else:
    print(args)
