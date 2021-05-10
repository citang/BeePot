import traceback

from twisted.application import service
from pkg_resources import iter_entry_points

from bee.config import config
from bee.logger import getLogger
from bee.modules.ssh import BeeSSH

ENTRYPOINT = "bee.usermodule"
MODULES = [BeeSSH]

logger = getLogger(config)


def start_mod(application, klass):
    try:
        obj = klass(config=config, logger=logger)
    except Exception as e:
        err = 'Failed to instantiate instance of class %s in %s. %s' % (
            klass.__name__,
            klass.__module__,
            traceback.format_exc()
        )
        logMsg({'logdata': err})
        return

    if hasattr(obj, 'startYourEngines'):
        try:
            obj.startYourEngines()
            msg = 'Ran startYourEngines on class %s in %s' % (
                klass.__name__,
                klass.__module__
            )
            logMsg({'logdata': msg})

        except Exception as e:
            err = 'Failed to run startYourEngines on %s in %s. %s' % (
                klass.__name__,
                klass.__module__,
                traceback.format_exc()
            )
            logMsg({'logdata': err})
    elif hasattr(obj, 'getService'):
        try:
            service = obj.getService()
            if not isinstance(service, list):
                service = [service]
            for s in service:
                s.setServiceParent(application)
            msg = 'Added service from class %s in %s to fake' % (
                klass.__name__,
                klass.__module__
            )
            logMsg({'logdata': msg})
        except Exception as e:
            err = 'Failed to add service from class %s in %s. %s' % (
                klass.__name__,
                klass.__module__,
                traceback.format_exc()
            )
            logMsg({'logdata': err})
    else:
        err = 'The class %s in %s does not have any required starting method.' % (
            klass.__name__,
            klass.__module__
        )
        logMsg({'logdata': err})


def logMsg(msg):
    data = {}
    #    data['src_host'] = device_name
    #    data['dst_host'] = node_id
    data['logdata'] = {'msg': msg}
    logger.log(data, retry=False)


application = service.Application("beed")

# List of modules to start
start_modules = []

# Add all custom modules
# (Permanently enabled as they don't officially use settings yet)
for ep in iter_entry_points(ENTRYPOINT):
    try:
        klass = ep.load(require=False)
        start_modules.append(klass)
    except Exception as e:
        err = 'Failed to load class from the entrypoint: %s. %s' % (
            str(ep),
            traceback.format_exc()
        )
        logMsg({'logdata': err})

# Add only enabled modules
start_modules.extend(filter(lambda m: config.moduleEnabled(m.NAME), MODULES))

for klass in start_modules:
    start_mod(application, klass)

msg = 'Bee running!!!'
logMsg({'logdata': msg})
