
import multipart, json, numpy, warnings
import requests


class raptureAPI:
    def __init__(self, url, user, password):
        if (url[0:7] == 'http://'):
            url = url[7:]
        if (url[0:8] == 'https://'):
            url = url[8:]
        mylist = url.split("/", 1)
        self.url = mylist[0]
        if len(mylist) ==1 or len(mylist[1]) == 0:
          self.prefix = ""
        else:
          self.prefix = "/" + mylist[1]
        self.session = requests.Session()
        # TODO: implement auth in terms of requests.auth so we can automatically
        # log back in
        self.login(user, password)

    def login(self, user, password):
        params={}
        params['user'] = user
        context={}
        try:
            context=self.runMultipart("/login","CONTEXT", params)
        except:
            raise ValueError("Unable to access " + self.url + self.prefix)
        if context['inError']:
            raise ValueError("Login failure: " + str(context['response']['message']))
        self.salt = context['response']['salt']
        self.contextid = context['response']['contextId']
        params = {}
        params['user'] = user
        params['context'] = self.contextid
        hashpassword = multipart.MD5(multipart.MD5(password) + ":" +self.salt)
        params['digest'] = hashpassword
        clientApiVersion = {}
        clientApiVersion['major'] = 2
        clientApiVersion['minor'] = 0
        clientApiVersion['micro'] = 0
        params['clientApiVersion'] = clientApiVersion
        res = self.runMultipart("/login", "LOGIN", params)
        if res['inError']:
            raise ValueError("Login failure: " + str(res['response']['message']))
        self.context = res['response']

# RAP-1126 JSON Encoder cannot handle objects of type numpy.int* so convert them to long first
# In Python 2.x longs have no limit. In 3.x I believe type conversion is automatic, but I'm not sure what versions we need to support.
# Any other parameter type tweaking can also be performed here as the need arises

    def fixTypes(self, obj):
        if (isinstance(obj, numpy.int64) | isinstance(obj, numpy.int32) | isinstance(obj, numpy.int16) | isinstance(obj, numpy.int8) | isinstance(obj, numpy.int0)) :
            return (long(obj))
        if (isinstance(obj, list)):
            # iterate through list and convert any numpy types. Note that lists can hold mixed types, so check each individually
            newlist = list(obj)
            for i in range (0, len(obj)):
                entry = obj[i]
                if (isinstance(entry, numpy.int64) | isinstance(entry, numpy.int32) | isinstance(entry, numpy.int16) | isinstance(entry, numpy.int8) | isinstance(entry, numpy.int0)) :
                    newlist[i] = long(entry)
            return newlist
        return obj

    def runMultipart(self, urlprefix, fnName, params):
        paramArray = [('FUNCTION',fnName),('PARAMS', json.dumps(params))]
        fullURL = self.prefix + urlprefix
        jsonString = multipart.post_multipart(self.session, self.url, fullURL, paramArray, [])
        try:
            result = json.loads(jsonString)
        except Exception:
            result = json.loads(jsonString.decode('cp1252').encode('utf-8'))

        if 'inError' in result and result['inError']:
            raise RuntimeError('Error returned from server. Response was:\n' + str(result['response']))
        else:
            return result


    def getClientApiVersion(self):
        return {u"major":2, u"minor":0, u"micro":0};

    def doActivity_CreateActivity(self,description,message,progress,max):
        '''
        This method creates and starts recording a new activity. It returns a unique id that
        can be used to update the status of the activity.
        '''
        params = {}
        params['context'] = self.context
        params['description'] = self.fixTypes(description)
        params['message'] = self.fixTypes(message)
        params['progress'] = self.fixTypes(progress)
        params['max'] = self.fixTypes(max)
        ret= self.runMultipart("/activity", "CREATEACTIVITY", params)
        return ret['response']

    def doActivity_UpdateActivity(self,activityId,message,progress,max):
        '''
        This method updates the status of an activity.  The return value is false if the
        activity was already marked as finished or aborted.  If the value is false, this
        function will not take effect.
        '''
        params = {}
        params['context'] = self.context
        params['activityId'] = self.fixTypes(activityId)
        params['message'] = self.fixTypes(message)
        params['progress'] = self.fixTypes(progress)
        params['max'] = self.fixTypes(max)
        ret= self.runMultipart("/activity", "UPDATEACTIVITY", params)
        return ret['response']

    def doActivity_FinishActivity(self,activityId,message):
        '''
        This method marks an activity as finished.  The return value is false if the activity
        was already marked as finished or aborted.  If the value is false, this function
        will not take effect.
        '''
        params = {}
        params['context'] = self.context
        params['activityId'] = self.fixTypes(activityId)
        params['message'] = self.fixTypes(message)
        ret= self.runMultipart("/activity", "FINISHACTIVITY", params)
        return ret['response']

    def doActivity_RequestAbortActivity(self,activityId,message):
        '''
        This method is used to request that an activity abort. This will indicate to callers
        of updateActivity that the request is aborted, via the return value  of calls that
        write to this activity, such as updateActivity or recordActivity.  The return value
        is false if the activity was already marked as finished or aborted.  If the value
        is false, this function will not take effect.
        '''
        params = {}
        params['context'] = self.context
        params['activityId'] = self.fixTypes(activityId)
        params['message'] = self.fixTypes(message)
        ret= self.runMultipart("/activity", "REQUESTABORTACTIVITY", params)
        return ret['response']

    def doActivity_QueryByExpiryTime(self,nextBatchId,batchSize,lastSeen):
        '''
        Retrieve activities updated after a given timestamp  - nextBatchId: the id for the
        batch, if this is not the first request. Empty string to indicate the first request
         - batchSize: the maximum number of items you want to see in this batch. Maximum
        is 10000 -- if the number passed in is > 10k, it gets set to 10k.  - lastSeen: an
        epoch timestamp in milliseconds. only activities that were last updated after this
        time will be returned
        '''
        params = {}
        params['context'] = self.context
        params['nextBatchId'] = self.fixTypes(nextBatchId)
        params['batchSize'] = self.fixTypes(batchSize)
        params['lastSeen'] = self.fixTypes(lastSeen)
        ret= self.runMultipart("/activity", "QUERYBYEXPIRYTIME", params)
        return ret['response']

    def doActivity_GetById(self,activityId):
        '''
        Get an activity by id
        '''
        params = {}
        params['context'] = self.context
        params['activityId'] = self.fixTypes(activityId)
        ret= self.runMultipart("/activity", "GETBYID", params)
        return ret['response']

    def doBootstrap_SetEmphemeralRepo(self,config):
        '''
        The ephemeral repository is used to store information that does not need to survive
        a restart of Rapture. It normally holds information such as sessions, and its config
        is usually based around a shared non-versioned memory model
        '''
        params = {}
        params['context'] = self.context
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/bootstrap", "SETEMPHEMERALREPO", params)
        return ret['response']

    def doBootstrap_SetConfigRepo(self,config):
        '''
        The config repository is used to store general config information about entities
        in Rapture. These entities include users, types, indices, queues and the like.
        '''
        params = {}
        params['context'] = self.context
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/bootstrap", "SETCONFIGREPO", params)
        return ret['response']

    def doBootstrap_SetSettingsRepo(self,config):
        '''
        The settings repository is used to store general low level settings in Rapture.
        '''
        params = {}
        params['context'] = self.context
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/bootstrap", "SETSETTINGSREPO", params)
        return ret['response']

    def doBootstrap_MigrateConfigRepo(self,newConfig):
        '''
        This method is used to migrate the top level Config repository to a new config. This
        task takes place in the background, and once completed the config repository is
        switched to the new config.   Any changes to config up to this point may be lost.
        '''
        params = {}
        params['context'] = self.context
        params['newConfig'] = self.fixTypes(newConfig)
        ret= self.runMultipart("/bootstrap", "MIGRATECONFIGREPO", params)
        return ret['response']

    def doBootstrap_MigrateEphemeralRepo(self,newConfig):
        '''
        This method is used to migrate the top level Ephemeral repository to a new config.
        This task takes place in the background, and once completed the config repository
        is switched to the new config.   Any changes to config up to this point may be lost.
        '''
        params = {}
        params['context'] = self.context
        params['newConfig'] = self.fixTypes(newConfig)
        ret= self.runMultipart("/bootstrap", "MIGRATEEPHEMERALREPO", params)
        return ret['response']

    def doBootstrap_MigrateSettingsRepo(self,newConfig):
        '''
        This method is used to migrate the top level Settings repository to a new config.
        This task takes place in the background, and once completed the config repository
        is switched to the new config.   Any changes to config up to this point may be lost.
        '''
        params = {}
        params['context'] = self.context
        params['newConfig'] = self.fixTypes(newConfig)
        ret= self.runMultipart("/bootstrap", "MIGRATESETTINGSREPO", params)
        return ret['response']

    def doBootstrap_GetConfigRepo(self):
        '''
        Retrieve the current settings of the config repository.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/bootstrap", "GETCONFIGREPO", params)
        return ret['response']

    def doBootstrap_GetSettingsRepo(self):
        '''
        Retrieve the current settings of the settings repository.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/bootstrap", "GETSETTINGSREPO", params)
        return ret['response']

    def doBootstrap_GetEphemeralRepo(self):
        '''
        Retrieve the current settings of the ephemeral repository.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/bootstrap", "GETEPHEMERALREPO", params)
        return ret['response']

    def doBootstrap_RestartBootstrap(self):
        '''
        After changing the definition of any bootstrap repository, Rapture will need to be
        restarted. This method will restart Rapture.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/bootstrap", "RESTARTBOOTSTRAP", params)
        return ret['response']

    def doBootstrap_AddScriptClass(self,keyword,className):
        '''
        All scripts that are run by Rapture are passed a set of helper instances that can
        be used by the script. The helpers are locked to the entitlement context of the
        calling user. This method sets the name of such a class in this context. It is primarily
        an internal function, defined during startup, as the class provided must be accessible
        by the main Rapture application.
        '''
        params = {}
        params['context'] = self.context
        params['keyword'] = self.fixTypes(keyword)
        params['className'] = self.fixTypes(className)
        ret= self.runMultipart("/bootstrap", "ADDSCRIPTCLASS", params)
        return ret['response']

    def doBootstrap_GetScriptClasses(self):
        '''
        This method retrieves previous defined script classes for this system
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/bootstrap", "GETSCRIPTCLASSES", params)
        return ret['response']

    def doBootstrap_DeleteScriptClass(self,keyword):
        '''
        This method removes a previously defined script class.
        '''
        params = {}
        params['context'] = self.context
        params['keyword'] = self.fixTypes(keyword)
        ret= self.runMultipart("/bootstrap", "DELETESCRIPTCLASS", params)
        return ret['response']

    def doScript_CreateScript(self,scriptURI,language,purpose,script):
        '''
        Creates a script in the system.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['language'] = self.fixTypes(language)
        params['purpose'] = self.fixTypes(purpose)
        params['script'] = self.fixTypes(script)
        ret= self.runMultipart("/script", "CREATESCRIPT", params)
        return ret['response']

    def doScript_CreateScriptLink(self,fromScriptURI,toScriptURI):
        '''
        Creates a symbolic link to a script in the system.
        '''
        params = {}
        params['context'] = self.context
        params['fromScriptURI'] = self.fixTypes(fromScriptURI)
        params['toScriptURI'] = self.fixTypes(toScriptURI)
        ret= self.runMultipart("/script", "CREATESCRIPTLINK", params)
        return ret['response']

    def doScript_RemoveScriptLink(self,fromScriptURI):
        '''
        Removes a symbolic link to a script in the system.
        '''
        params = {}
        params['context'] = self.context
        params['fromScriptURI'] = self.fixTypes(fromScriptURI)
        ret= self.runMultipart("/script", "REMOVESCRIPTLINK", params)
        return ret['response']

    def doScript_SetScriptParameters(self,scriptURI,parameters):
        '''
        Sets the parameters that should be used for a script. Parameters are the names of
        the arguments that should be passed in, not the argument values themselves.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['parameters'] = self.fixTypes(parameters)
        ret= self.runMultipart("/script", "SETSCRIPTPARAMETERS", params)
        return ret['response']

    def doScript_DoesScriptExist(self,scriptURI):
        '''
        Returns true the given script was found.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        ret= self.runMultipart("/script", "DOESSCRIPTEXIST", params)
        return ret['response']

    def doScript_DeleteScript(self,scriptURI):
        '''
        Removes the script from the system.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        ret= self.runMultipart("/script", "DELETESCRIPT", params)
        return ret['response']

    def doScript_GetScriptNames(self,scriptURI):
        '''
        Retrieves all of the scripts within a authority.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        ret= self.runMultipart("/script", "GETSCRIPTNAMES", params)
        return ret['response']

    def doScript_GetScript(self,scriptURI):
        '''
        Retrieves the contents of a script.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        ret= self.runMultipart("/script", "GETSCRIPT", params)
        return ret['response']

    def doScript_PutScript(self,scriptURI,script):
        '''
        Stores a script in the system using a RaptureScript object.  TODO is there really
        any point in passing the URI? The storage location is based on RaptureScript. All
        we do is extract the Authority from the URI; the caller can do that.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['script'] = self.fixTypes(script)
        ret= self.runMultipart("/script", "PUTSCRIPT", params)
        return ret['response']

    def doScript_PutRawScript(self,scriptURI,content,language,purpose,param_types,param_names):
        '''
        Store a script in the system using raw inputs. Most users will want the value PROGRAM
        for purpose.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['content'] = self.fixTypes(content)
        params['language'] = self.fixTypes(language)
        params['purpose'] = self.fixTypes(purpose)
        params['param_types'] = self.fixTypes(param_types)
        params['param_names'] = self.fixTypes(param_names)
        ret= self.runMultipart("/script", "PUTRAWSCRIPT", params)
        return ret['response']

    def doScript_RunScript(self,scriptURI,parameters):
        '''
        Run a script in the Rapture environment.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['parameters'] = self.fixTypes(parameters)
        ret= self.runMultipart("/script", "RUNSCRIPT", params)
        return ret['response']

    def doScript_RunScriptExtended(self,scriptURI,parameters):
        '''
        Runs a script in the Rapture environment.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['parameters'] = self.fixTypes(parameters)
        ret= self.runMultipart("/script", "RUNSCRIPTEXTENDED", params)
        return ret['response']

    def doScript_CheckScript(self,scriptURI):
        '''
        Parses the script and returns any error messages from the parsing process. If the
        String returned is empty the script is valid Reflex.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        ret= self.runMultipart("/script", "CHECKSCRIPT", params)
        return ret['response']

    def doScript_CreateREPLSession(self):
        '''
        Creates a Reflex REPL session that can be written to. These sessions eventually die
        if not used  or killed
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/script", "CREATEREPLSESSION", params)
        return ret['response']

    def doScript_DestroyREPLSession(self,sessionId):
        '''
        Kills an existing Reflex REPL session.
        '''
        params = {}
        params['context'] = self.context
        params['sessionId'] = self.fixTypes(sessionId)
        ret= self.runMultipart("/script", "DESTROYREPLSESSION", params)
        return ret['response']

    def doScript_EvaluateREPL(self,sessionId,line):
        '''
        Adds a line to the current Reflex session, returns back what the parser/evaluator
        says
        '''
        params = {}
        params['context'] = self.context
        params['sessionId'] = self.fixTypes(sessionId)
        params['line'] = self.fixTypes(line)
        ret= self.runMultipart("/script", "EVALUATEREPL", params)
        return ret['response']

    def doScript_ArchiveOldREPLSessions(self,ageInMinutes):
        '''
        Archive/delete old REPL sessions
        '''
        params = {}
        params['context'] = self.context
        params['ageInMinutes'] = self.fixTypes(ageInMinutes)
        ret= self.runMultipart("/script", "ARCHIVEOLDREPLSESSIONS", params)
        return ret['response']

    def doScript_CreateSnippet(self,snippetURI,snippet):
        '''
        Creates a code snippet and stores it in Rapture.
        '''
        params = {}
        params['context'] = self.context
        params['snippetURI'] = self.fixTypes(snippetURI)
        params['snippet'] = self.fixTypes(snippet)
        ret= self.runMultipart("/script", "CREATESNIPPET", params)
        return ret['response']

    def doScript_GetSnippetChildren(self,prefix):
        '''
        Returns all children snippets with a given prefix.
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        ret= self.runMultipart("/script", "GETSNIPPETCHILDREN", params)
        return ret['response']

    def doScript_DeleteSnippet(self,snippetURI):
        '''
        Deletes a snippet by its URI.
        '''
        params = {}
        params['context'] = self.context
        params['snippetURI'] = self.fixTypes(snippetURI)
        ret= self.runMultipart("/script", "DELETESNIPPET", params)
        return ret['response']

    def doScript_GetSnippet(self,snippetURI):
        '''
        Retrieves a snippet by its URI.
        '''
        params = {}
        params['context'] = self.context
        params['snippetURI'] = self.fixTypes(snippetURI)
        ret= self.runMultipart("/script", "GETSNIPPET", params)
        return ret['response']

    def doScript_ListScriptsByUriPrefix(self,uriPrefix,depth):
        '''
        Returns full pathnames for an entire subtree as a map of path to RFI.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/script", "LISTSCRIPTSBYURIPREFIX", params)
        return ret['response']

    def doScript_DeleteScriptsByUriPrefix(self,uriPrefix):
        '''
        Removes a folder and its contents recursively, including empty subfolders. Returns
        a list of the scripts and folders removed.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        ret= self.runMultipart("/script", "DELETESCRIPTSBYURIPREFIX", params)
        return ret['response']

    def doLock_GetLockManagerConfigs(self,managerUri):
        '''
        Retrieves the lock providers for a given authority.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        ret= self.runMultipart("/lock", "GETLOCKMANAGERCONFIGS", params)
        return ret['response']

    def doLock_CreateLockManager(self,managerUri,config,pathPosition):
        '''
        Creates a lock provider with an authority.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        params['config'] = self.fixTypes(config)
        params['pathPosition'] = self.fixTypes(pathPosition)
        ret= self.runMultipart("/lock", "CREATELOCKMANAGER", params)
        return ret['response']

    def doLock_LockManagerExists(self,managerUri):
        '''
        Returns true if the lock providers found.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        ret= self.runMultipart("/lock", "LOCKMANAGEREXISTS", params)
        return ret['response']

    def doLock_GetLockManagerConfig(self,managerUri):
        '''
        Gets a lock provider by its Uri.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        ret= self.runMultipart("/lock", "GETLOCKMANAGERCONFIG", params)
        return ret['response']

    def doLock_DeleteLockManager(self,managerUri):
        '''
        Deletes a lock provider by its Uri.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        ret= self.runMultipart("/lock", "DELETELOCKMANAGER", params)
        return ret['response']

    def doLock_AcquireLock(self,managerUri,lockName,secondsToWait,secondsToKeep):
        '''
        Acquire a lock. Returns a LockHandle, which you need to pass to releaseLock when
        calling it. Ifunable to acquire the lock, returns null.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        params['lockName'] = self.fixTypes(lockName)
        params['secondsToWait'] = self.fixTypes(secondsToWait)
        params['secondsToKeep'] = self.fixTypes(secondsToKeep)
        ret= self.runMultipart("/lock", "ACQUIRELOCK", params)
        return ret['response']

    def doLock_ReleaseLock(self,managerUri,lockName,lockHandle):
        '''
        Releases a lock.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        params['lockName'] = self.fixTypes(lockName)
        params['lockHandle'] = self.fixTypes(lockHandle)
        ret= self.runMultipart("/lock", "RELEASELOCK", params)
        return ret['response']

    def doLock_ForceReleaseLock(self,managerUri,lockName):
        '''
        This is a dangerous variant of release lock that will kick someone else off the lock
        queue.
        '''
        params = {}
        params['context'] = self.context
        params['managerUri'] = self.fixTypes(managerUri)
        params['lockName'] = self.fixTypes(lockName)
        ret= self.runMultipart("/lock", "FORCERELEASELOCK", params)
        return ret['response']

    def doNotification_GetNotificationManagerConfigs(self):
        '''
        This method retrieves the notification providers in use at this Rapture system.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/notification", "GETNOTIFICATIONMANAGERCONFIGS", params)
        return ret['response']

    def doNotification_ListNotificationsByUriPrefix(self,uriPrefix):
        '''
        Returns a list of full display names of the paths below this one. Ideally optimized
        depending on the repo.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        ret= self.runMultipart("/notification", "LISTNOTIFICATIONSBYURIPREFIX", params)
        return ret['response']

    def doNotification_FindNotificationManagerConfigsByPurpose(self,purpose):
        '''
        Notification providers have an associated purpose - this method returns only those
        providers that match the given purpose.
        '''
        params = {}
        params['context'] = self.context
        params['purpose'] = self.fixTypes(purpose)
        ret= self.runMultipart("/notification", "FINDNOTIFICATIONMANAGERCONFIGSBYPURPOSE", params)
        return ret['response']

    def doNotification_CreateNotificationManager(self,notificationManagerUri,config,purpose):
        '''
        This method creates a definition of a notification provider.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        params['config'] = self.fixTypes(config)
        params['purpose'] = self.fixTypes(purpose)
        ret= self.runMultipart("/notification", "CREATENOTIFICATIONMANAGER", params)
        return ret['response']

    def doNotification_NotificationManagerExists(self,notificationManagerUri):
        '''
        Indicates whether a notification provider with notificationName was found.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        ret= self.runMultipart("/notification", "NOTIFICATIONMANAGEREXISTS", params)
        return ret['response']

    def doNotification_GetNotificationManagerConfig(self,notificationManagerUri):
        '''
        This method returns the low level config for a given notification provider.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        ret= self.runMultipart("/notification", "GETNOTIFICATIONMANAGERCONFIG", params)
        return ret['response']

    def doNotification_DeleteNotificationManager(self,notificationManagerUri):
        '''
        This method removes a notification provider and all its content.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        ret= self.runMultipart("/notification", "DELETENOTIFICATIONMANAGER", params)
        return ret['response']

    def doNotification_GetLatestNotificationEpoch(self,notificationManagerUri):
        '''
        This method retrieves the current epoch number for a given notification point.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        ret= self.runMultipart("/notification", "GETLATESTNOTIFICATIONEPOCH", params)
        return ret['response']

    def doNotification_PublishNotification(self,notificationManagerUri,referenceId,content,contentType):
        '''
        This method pushes a notification to a provider.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        params['referenceId'] = self.fixTypes(referenceId)
        params['content'] = self.fixTypes(content)
        params['contentType'] = self.fixTypes(contentType)
        ret= self.runMultipart("/notification", "PUBLISHNOTIFICATION", params)
        return ret['response']

    def doNotification_FindNotificationsAfterEpoch(self,notificationManagerUri,epoch):
        '''
        This method returns the changes seen on a notification since an epoch. A client would
        then update its latest epoch by using the value in the   notification result.
        '''
        params = {}
        params['context'] = self.context
        params['notificationManagerUri'] = self.fixTypes(notificationManagerUri)
        params['epoch'] = self.fixTypes(epoch)
        ret= self.runMultipart("/notification", "FINDNOTIFICATIONSAFTEREPOCH", params)
        return ret['response']

    def doNotification_GetNotification(self,notificationUri,id):
        '''
        This method returns a notification message given its id.
        '''
        params = {}
        params['context'] = self.context
        params['notificationUri'] = self.fixTypes(notificationUri)
        params['id'] = self.fixTypes(id)
        ret= self.runMultipart("/notification", "GETNOTIFICATION", params)
        return ret['response']

    def doTable_CreateTable(self,indexURI,config):
        '''
        @Deprecated: The Table api is deprecated, use the index api instead 
        Creates a RaptureTableConfig object with the specified configuration and stores it
        in the config repo.
        '''
        warnings.warn(
           'doTable_CreateTable The Table api is deprecated, use the index api instead',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['indexURI'] = self.fixTypes(indexURI)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/table", "CREATETABLE", params)
        return ret['response']

    def doTable_GetTablesForAuthority(self,authority):
        '''
        @Deprecated: The Table api is deprecated, use the index api instead 
        Gets the configs for all tables in a given authority.
        '''
        warnings.warn(
           'doTable_GetTablesForAuthority The Table api is deprecated, use the index api instead',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['authority'] = self.fixTypes(authority)
        ret= self.runMultipart("/table", "GETTABLESFORAUTHORITY", params)
        return ret['response']

    def doTable_GetTable(self,indexURI):
        '''
        @Deprecated: The Table api is deprecated, use the index api instead 
        Gets the config for a specified table.
        '''
        warnings.warn(
           'doTable_GetTable The Table api is deprecated, use the index api instead',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['indexURI'] = self.fixTypes(indexURI)
        ret= self.runMultipart("/table", "GETTABLE", params)
        return ret['response']

    def doTable_DeleteTable(self,indexURI):
        '''
        @Deprecated: The Table api is deprecated, use the index api instead 
        Deletes a RaptureTableConfig from the config repo.
        '''
        warnings.warn(
           'doTable_DeleteTable The Table api is deprecated, use the index api instead',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['indexURI'] = self.fixTypes(indexURI)
        ret= self.runMultipart("/table", "DELETETABLE", params)
        return ret['response']

    def doTable_QueryTable(self,indexURI,query):
        '''
        @Deprecated: The Table api is deprecated, use the index api instead 
        Runs a TableQuery on a given table/index URI.
        '''
        warnings.warn(
           'doTable_QueryTable The Table api is deprecated, use the index api instead',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['indexURI'] = self.fixTypes(indexURI)
        params['query'] = self.fixTypes(query)
        ret= self.runMultipart("/table", "QUERYTABLE", params)
        return ret['response']

    def doIndex_CreateIndex(self,indexUri,config):
        '''
        Generates a new index for the repository. Note that objects are indexed only when
        they are written. Any objects already in the repository are not automatically indexed;
        they need to be read and written back.
        '''
        params = {}
        params['context'] = self.context
        params['indexUri'] = self.fixTypes(indexUri)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/index", "CREATEINDEX", params)
        return ret['response']

    def doIndex_GetIndex(self,indexUri):
        '''
        Gets the config for a specified index.
        '''
        params = {}
        params['context'] = self.context
        params['indexUri'] = self.fixTypes(indexUri)
        ret= self.runMultipart("/index", "GETINDEX", params)
        return ret['response']

    def doIndex_DeleteIndex(self,indexUri):
        '''
        Removes an index.
        '''
        params = {}
        params['context'] = self.context
        params['indexUri'] = self.fixTypes(indexUri)
        ret= self.runMultipart("/index", "DELETEINDEX", params)
        return ret['response']

    def doIndex_FindIndex(self,indexUri,query):
        '''
        findIndex uses a simple structure of the form SELECT (DISTINCT) field (,field...)
        WHERE condition (,condition...) (ORDER BY field (DESC) )Example: SELECT DISTINCT
        foo, bar WHERE baz = "wibble" ORDER BY foo
        '''
        params = {}
        params['context'] = self.context
        params['indexUri'] = self.fixTypes(indexUri)
        params['query'] = self.fixTypes(query)
        ret= self.runMultipart("/index", "FINDINDEX", params)
        return ret['response']

    def doAdmin_GetSystemProperties(self,keys):
        '''
        This function retrieves the system properties in use for this instance of Rapture.
        As system propertiesare often used to control external connectivity, a client can
        determine the inferred connectivity endpointsby using this api call. It returns
        a map from system property name (the key) to value. You cannot modify thesystem
        properties of Rapture through the api, they are set by the administrator as part
        of the general setup of a Rapturesystem. Note that this call returns the properties
        for the actual end point that the client is connected to, it is not necessarily
        true thatthe same properties will be set for every API endpoint.
        '''
        params = {}
        params['context'] = self.context
        params['keys'] = self.fixTypes(keys)
        ret= self.runMultipart("/admin", "GETSYSTEMPROPERTIES", params)
        return ret['response']

    def doAdmin_GetRepoConfig(self):
        '''
        Rapture is a hierarchical set of repositories, and this method returns the config
        of the top most level - that usedfor general config and temporary (transient) values
        such as sessions. In clustered mode these configs wouldbe referencing shared storage,
        and in test mode they would normally refer to in-memory versions of the config.
        The manipulation of the top level config can be performed through the Bootstrap
        API.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETREPOCONFIG", params)
        return ret['response']

    def doAdmin_GetSessionsForUser(self,user):
        '''
        When a user logs into Rapture they create a transient session and this method is
        a way of retrieving all of the sessions for a given user. The CallingContext is
        a common object passed around Rapture api calls.
        '''
        params = {}
        params['context'] = self.context
        params['user'] = self.fixTypes(user)
        ret= self.runMultipart("/admin", "GETSESSIONSFORUSER", params)
        return ret['response']

    def doAdmin_GetTags(self,raptureURI):
        '''
        A type that is using a versioned repository will be able to use tags - these are
        fixed points in time (that are invariant) that reflect what the repository looked
        like when the tag was created. For example a tag could be assigned to a repository
        that marks the end of day view for a repository. Any changes made after this tag
        was created will be accessible in the normal perspective but will not be associated
        with the tag. This method returns all of the tags associated with this type in the
        given authority.
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/admin", "GETTAGS", params)
        return ret['response']

    def doAdmin_DeleteUser(self,userName):
        '''
        This method removes a user from this Rapture system. The user is removed from all
        entitlement groups also. The actualuser definition is retained and marked as inactive
        (so the user cannot login). This is because the user may still be referenced in
        audit trails and the change history in type repositories.
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/admin", "DELETEUSER", params)
        return ret['response']

    def doAdmin_DestroyUser(self,userName):
        '''
        This method destroys a user record. The user must have been previously disabled using
        'deleteUser' before this method may be called. This is a severe method that should
        only be used in non-production machines or to correct an administrativeerror in
        creating an account with the wrong name before that account has been used. Reference
        to the missing user may stillexist, and may not display properly in some UIs
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/admin", "DESTROYUSER", params)
        return ret['response']

    def doAdmin_RestoreUser(self,userName):
        '''
        This method restores a user that has been deleted
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/admin", "RESTOREUSER", params)
        return ret['response']

    def doAdmin_AddUser(self,userName,description,hashPassword,email):
        '''
        This method adds a user to the Rapture environment. The user will be in no entitlement
        groups by default. The passwordfield passed is actually the MD5 hash of the password
        - or at least the same hash function that will be applied whenlogging in to the
        system (the password is hashed, and then hashed again with the salt returned during
        the login protocol).
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        params['description'] = self.fixTypes(description)
        params['hashPassword'] = self.fixTypes(hashPassword)
        params['email'] = self.fixTypes(email)
        ret= self.runMultipart("/admin", "ADDUSER", params)
        return ret['response']

    def doAdmin_DoesUserExist(self,userName):
        '''
        This api call can be used to determine whether a given user exists in the Rapture
        system. Only system administrators can use this api call.
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/admin", "DOESUSEREXIST", params)
        return ret['response']

    def doAdmin_GetUser(self,userName):
        '''
        Retrieve a single user given their name.
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/admin", "GETUSER", params)
        return ret['response']

    def doAdmin_GenerateApiUser(self,prefix,description):
        '''
        Generates an api user, for use in connecting to Rapture in a relatively opaque way
        using a shared secret. An api user can log in with their access key without a password.
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        params['description'] = self.fixTypes(description)
        ret= self.runMultipart("/admin", "GENERATEAPIUSER", params)
        return ret['response']

    def doAdmin_ResetUserPassword(self,userName,newHashPassword):
        '''
        This method gives an administrator the ability to reset the password of a user. The
        user will have the new password passed. The newHashPassword parameter should be
        an MD5 of the new password - internally this will be hashed further against a salt
        for this user.
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        params['newHashPassword'] = self.fixTypes(newHashPassword)
        ret= self.runMultipart("/admin", "RESETUSERPASSWORD", params)
        return ret['response']

    def doAdmin_CreatePasswordResetToken(self,username):
        '''
        Creates password reset token
        '''
        params = {}
        params['context'] = self.context
        params['username'] = self.fixTypes(username)
        ret= self.runMultipart("/admin", "CREATEPASSWORDRESETTOKEN", params)
        return ret['response']

    def doAdmin_CancelPasswordResetToken(self,username):
        '''
        Cancels password reset token
        '''
        params = {}
        params['context'] = self.context
        params['username'] = self.fixTypes(username)
        ret= self.runMultipart("/admin", "CANCELPASSWORDRESETTOKEN", params)
        return ret['response']

    def doAdmin_UpdateUserEmail(self,userName,newEmail):
        '''
        This method updates user email.
        '''
        params = {}
        params['context'] = self.context
        params['userName'] = self.fixTypes(userName)
        params['newEmail'] = self.fixTypes(newEmail)
        ret= self.runMultipart("/admin", "UPDATEUSEREMAIL", params)
        return ret['response']

    def doAdmin_GetRemotes(self):
        '''
        This method lists the remotes created on this system (the connections this system
        may make to other systems).
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETREMOTES", params)
        return ret['response']

    def doAdmin_AddRemote(self,name,description,url,apiKey,optP):
        '''
        Remotes are used to connect one Rapture cloud environment to another. Each remote
        manages a connection to another Rapture cloudthrough the http api. This method adds
        a new remote to this system. The apikey is the login name of a user on the remote
        cloud with adequate entitlements to push and pull thedata to be synchronized or
        accessed via the remote. The description can be any text to help the human administrators
        tell clouds apart.The url is the http end point of the remote system.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['description'] = self.fixTypes(description)
        params['url'] = self.fixTypes(url)
        params['apiKey'] = self.fixTypes(apiKey)
        params['optP'] = self.fixTypes(optP)
        ret= self.runMultipart("/admin", "ADDREMOTE", params)
        return ret['response']

    def doAdmin_DeleteRemote(self,name):
        '''
        This method deletes a previously created remote.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/admin", "DELETEREMOTE", params)
        return ret['response']

    def doAdmin_UpdateRemoteApiKey(self,name,apiKey):
        '''
        This method updates the user api key used by a given remote. This is an api key for
        the remote system, not this Rapture system.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['apiKey'] = self.fixTypes(apiKey)
        ret= self.runMultipart("/admin", "UPDATEREMOTEAPIKEY", params)
        return ret['response']

    def doAdmin_SetRemote(self,raptureURI,remote,remoteURI):
        '''
        A remote has been defined it can be used to synchronize one repository with another.
        This method defines how one (local) repository is connected to a remote type. The
        binding is made between the combination of a authority, repository and perspective
        from one system to another. The previously defines remote will hand the synchronization
        work.
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['remote'] = self.fixTypes(remote)
        params['remoteURI'] = self.fixTypes(remoteURI)
        ret= self.runMultipart("/admin", "SETREMOTE", params)
        return ret['response']

    def doAdmin_ClearRemote(self,raptureURI):
        '''
        This method reverses a previously defined association between two repositories
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/admin", "CLEARREMOTE", params)
        return ret['response']

    def doAdmin_PullRemote(self,raptureURI):
        '''
        If this type has a remote defined, use it to sync this repository with that of the
        other.
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/admin", "PULLREMOTE", params)
        return ret['response']

    def doAdmin_AddTemplate(self,name,template,overwrite):
        '''
        This function adds a template to the Rapture system. A template is a simple way of
        registering predefined configs that can be used to automatically generate configs
        for repositories, queues, and the like.    Templates use the popular StringTemplate
        library for merging values into a text template.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['template'] = self.fixTypes(template)
        params['overwrite'] = self.fixTypes(overwrite)
        ret= self.runMultipart("/admin", "ADDTEMPLATE", params)
        return ret['response']

    def doAdmin_RunTemplate(self,name,parameters):
        '''
        This method executes a template, replacing parts of the template with the passed
        parameters to create a new string.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['parameters'] = self.fixTypes(parameters)
        ret= self.runMultipart("/admin", "RUNTEMPLATE", params)
        return ret['response']

    def doAdmin_GetTemplate(self,name):
        '''
        This method returns the definition of a template.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/admin", "GETTEMPLATE", params)
        return ret['response']

    def doAdmin_CopyDocumentRepo(self,srcAuthority,targAuthority,wipe):
        '''
        Copies the data from one DocumentRepo to another. The target repository is wiped
        out before hand if 'wipe' is set to true. The target must already exist when this
        method is called.
        '''
        params = {}
        params['context'] = self.context
        params['srcAuthority'] = self.fixTypes(srcAuthority)
        params['targAuthority'] = self.fixTypes(targAuthority)
        params['wipe'] = self.fixTypes(wipe)
        ret= self.runMultipart("/admin", "COPYDOCUMENTREPO", params)
        return ret['response']

    def doAdmin_AddIPToWhiteList(self,ipAddress):
        '''
        Use this method to add an IP address to a white list of allowed IP addresses that
        can log in to this Rapture environment. Once set only IP addresses in this ipAddress
        list can access Rapture. By default there are no whitelist IP addresses defined
        which actually means that all IP addresses are allowed.
        '''
        params = {}
        params['context'] = self.context
        params['ipAddress'] = self.fixTypes(ipAddress)
        ret= self.runMultipart("/admin", "ADDIPTOWHITELIST", params)
        return ret['response']

    def doAdmin_RemoveIPFromWhiteList(self,ipAddress):
        '''
        Use this method to remove an IP address from a white list
        '''
        params = {}
        params['context'] = self.context
        params['ipAddress'] = self.fixTypes(ipAddress)
        ret= self.runMultipart("/admin", "REMOVEIPFROMWHITELIST", params)
        return ret['response']

    def doAdmin_GetIPWhiteList(self):
        '''
        Use this method to return the IP white list
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETIPWHITELIST", params)
        return ret['response']

    def doAdmin_RunBatchScript(self,script):
        '''
        This method runs a batch script at the target site
        '''
        params = {}
        params['context'] = self.context
        params['script'] = self.fixTypes(script)
        ret= self.runMultipart("/admin", "RUNBATCHSCRIPT", params)
        return ret['response']

    def doAdmin_GetAllUsers(self):
        '''
        This method retrieves all of the registered users in the system
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETALLUSERS", params)
        return ret['response']

    def doAdmin_InitiateTypeConversion(self,raptureURI,newConfig,versionsToKeep):
        '''
        This method kicks off a process that will migrate a DocumentRepo to an alternate
        config. A temporary type will be created with the new config,the old type will be
        locked for modifications and then all of the documents in the existing type will
        be copied to the new type, with the metadata intact.Optionally a number of historical
        versions will be kept if the source repository (and target) support it. Once all
        of the data has been copied the configattached to each type will be swapped and
        the type released for access. The temporary type will then be dropped.
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['newConfig'] = self.fixTypes(newConfig)
        params['versionsToKeep'] = self.fixTypes(versionsToKeep)
        ret= self.runMultipart("/admin", "INITIATETYPECONVERSION", params)
        return ret['response']

    def doAdmin_PutArchiveConfig(self,raptureURI,config):
        '''
        Set the archive config for a type
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/admin", "PUTARCHIVECONFIG", params)
        return ret['response']

    def doAdmin_GetArchiveConfig(self,raptureURI):
        '''
        Retrieve the archive config for a authority
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/admin", "GETARCHIVECONFIG", params)
        return ret['response']

    def doAdmin_DeleteArchiveConfig(self,raptureURI):
        '''
        Delete the archive config for a authority
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/admin", "DELETEARCHIVECONFIG", params)
        return ret['response']

    def doAdmin_Ping(self):
        '''
        A general purpose function that tests (or refreshes) the api connection to Rapture
        with no side effects.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "PING", params)
        return ret['response']

    def doAdmin_AddMetadata(self,values,overwrite):
        '''
        This function adds values to the metadata field of the CallingContext. It's used
        to hold values specific to this connection.    Since it's set by the caller the
        values cannot be considered entirely trusted, and private or secure data such as
        passwords shouldn't be stored in here.   If overwrite is false and an entry already
        exists then an exception should be thrown
        '''
        params = {}
        params['context'] = self.context
        params['values'] = self.fixTypes(values)
        params['overwrite'] = self.fixTypes(overwrite)
        ret= self.runMultipart("/admin", "ADDMETADATA", params)
        return ret['response']

    def doAdmin_SetMOTD(self,message):
        '''
        Set the MOTD (message of the day) for this environment. Setting to a zero length
        string implies that there is no message of the day
        '''
        params = {}
        params['context'] = self.context
        params['message'] = self.fixTypes(message)
        ret= self.runMultipart("/admin", "SETMOTD", params)
        return ret['response']

    def doAdmin_GetMOTD(self):
        '''
        Retrieve the MOTD
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETMOTD", params)
        return ret['response']

    def doAdmin_SetEnvironmentName(self,name):
        '''
        Set the name of this environment
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/admin", "SETENVIRONMENTNAME", params)
        return ret['response']

    def doAdmin_SetEnvironmentProperties(self,properties):
        '''
        Set the properties of this environment. Usually for displaying then name (e.g. BANNER_COLOR)
        '''
        params = {}
        params['context'] = self.context
        params['properties'] = self.fixTypes(properties)
        ret= self.runMultipart("/admin", "SETENVIRONMENTPROPERTIES", params)
        return ret['response']

    def doAdmin_GetEnvironmentName(self):
        '''
        Get the name of this environment
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETENVIRONMENTNAME", params)
        return ret['response']

    def doAdmin_GetEnvironmentProperties(self):
        '''
        Get the properties of this environment
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/admin", "GETENVIRONMENTPROPERTIES", params)
        return ret['response']

    def doAdmin_Encode(self,toEncode):
        '''
        Encode a String using the default encoding mechanism
        '''
        params = {}
        params['context'] = self.context
        params['toEncode'] = self.fixTypes(toEncode)
        ret= self.runMultipart("/admin", "ENCODE", params)
        return ret['response']

    def doAdmin_CreateURI(self,path,leaf):
        '''
        Create a URI with proper encoding given a path and a leaf. Normal URI characters
        such as : or / in the path will not be encoded
        '''
        params = {}
        params['context'] = self.context
        params['path'] = self.fixTypes(path)
        params['leaf'] = self.fixTypes(leaf)
        ret= self.runMultipart("/admin", "CREATEURI", params)
        return ret['response']

    def doAdmin_CreateMultipartURI(self,elements):
        '''
        Create a URI with proper encoding given a list of elements. The return value will
        begin with // Each element will be encoded    (including all punctuation characters)
        and the elements joined together separated by /
        '''
        params = {}
        params['context'] = self.context
        params['elements'] = self.fixTypes(elements)
        ret= self.runMultipart("/admin", "CREATEMULTIPARTURI", params)
        return ret['response']

    def doAdmin_Decode(self,encoded):
        '''
        Decode the supplied String according to the URI encoding/decoding rules
        '''
        params = {}
        params['context'] = self.context
        params['encoded'] = self.fixTypes(encoded)
        ret= self.runMultipart("/admin", "DECODE", params)
        return ret['response']

    def doAdmin_FindGroupNamesByUser(self,username):
        '''
        Find the groups for a given user and return just the names
        '''
        params = {}
        params['context'] = self.context
        params['username'] = self.fixTypes(username)
        ret= self.runMultipart("/admin", "FINDGROUPNAMESBYUSER", params)
        return ret['response']

    def doIdGen_GetIdGenConfigs(self,authority):
        '''
        Gets a list of idGens that have the given authority. Each idGen has a URI, and the
        authority is part of the URI. idGens whose URIs have an authority that matches the
        passed parameter will be returned.
        '''
        params = {}
        params['context'] = self.context
        params['authority'] = self.fixTypes(authority)
        ret= self.runMultipart("/idgen", "GETIDGENCONFIGS", params)
        return ret['response']

    def doIdGen_GetIdGenConfig(self,idGenUri):
        '''
        Retrieves a single idGen config given its name.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        ret= self.runMultipart("/idgen", "GETIDGENCONFIG", params)
        return ret['response']

    def doIdGen_CreateIdGen(self,idGenUri,config):
        '''
        This method is used to define a new idGen in a given authority. The config parameter
        defines the storage to be used for managing the idGen.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/idgen", "CREATEIDGEN", params)
        return ret['response']

    def doIdGen_IdGenExists(self,idGenUri):
        '''
        Returns true if the idGen was found.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        ret= self.runMultipart("/idgen", "IDGENEXISTS", params)
        return ret['response']

    def doIdGen_DeleteIdGen(self,idGenUri):
        '''
        This method is used to delete a previously defined idGen.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        ret= self.runMultipart("/idgen", "DELETEIDGEN", params)
        return ret['response']

    def doIdGen_SetIdGen(self,idGenUri,count):
        '''
        This method can be used to reset an idGen to a new id - all future requests will
        start from this new point.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        params['count'] = self.fixTypes(count)
        ret= self.runMultipart("/idgen", "SETIDGEN", params)
        return ret['response']

    def doIdGen_Next(self,idGenUri):
        '''
        This method is used to increment the idGen and returns a string that corresponds
        to the newly generated id.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        ret= self.runMultipart("/idgen", "NEXT", params)
        return ret['response']

    def doIdGen_NextIds(self,idGenUri,num):
        '''
        This method is used to increment the idGen by given amount and returns a string that
        corresponds to the newly generated id.
        '''
        params = {}
        params['context'] = self.context
        params['idGenUri'] = self.fixTypes(idGenUri)
        params['num'] = self.fixTypes(num)
        ret= self.runMultipart("/idgen", "NEXTIDS", params)
        return ret['response']

    def doIdGen_SetupDefaultIdGens(self,force):
        '''
        Sets up any idGens needed by Rapture by default, should be called from any startup
        scripts. If force is set to true, it will force the configto be set up again, even
        if it already exists.
        '''
        params = {}
        params['context'] = self.context
        params['force'] = self.fixTypes(force)
        ret= self.runMultipart("/idgen", "SETUPDEFAULTIDGENS", params)
        return ret['response']

    def doEntitlement_GetEntitlements(self):
        '''
        This method is used to retrieve all of the entitlements defined in Rapture.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/entitlement", "GETENTITLEMENTS", params)
        return ret['response']

    def doEntitlement_GetEntitlement(self,entitlementName):
        '''
        Retrieves a single entitlement, or null if not found.
        '''
        params = {}
        params['context'] = self.context
        params['entitlementName'] = self.fixTypes(entitlementName)
        ret= self.runMultipart("/entitlement", "GETENTITLEMENT", params)
        return ret['response']

    def doEntitlement_GetEntitlementByAddress(self,entitlementURI):
        '''
        Retrieves a single entitlement by using its URI.
        '''
        params = {}
        params['context'] = self.context
        params['entitlementURI'] = self.fixTypes(entitlementURI)
        ret= self.runMultipart("/entitlement", "GETENTITLEMENTBYADDRESS", params)
        return ret['response']

    def doEntitlement_GetEntitlementGroup(self,groupName):
        '''
        Retrieves a single entitlement group.
        '''
        params = {}
        params['context'] = self.context
        params['groupName'] = self.fixTypes(groupName)
        ret= self.runMultipart("/entitlement", "GETENTITLEMENTGROUP", params)
        return ret['response']

    def doEntitlement_GetEntitlementGroupByAddress(self,groupURI):
        '''
        Retrieves a single entitlement group from its URI.
        '''
        params = {}
        params['context'] = self.context
        params['groupURI'] = self.fixTypes(groupURI)
        ret= self.runMultipart("/entitlement", "GETENTITLEMENTGROUPBYADDRESS", params)
        return ret['response']

    def doEntitlement_GetEntitlementGroups(self):
        '''
        This method returns all of the entitlement groups defined in the Rapture environment.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/entitlement", "GETENTITLEMENTGROUPS", params)
        return ret['response']

    def doEntitlement_AddEntitlement(self,entitlementName,initialGroup):
        '''
        This method adds a new entitlement, specifying an initial group that should be assigned
        to this entitlement. The reason for assigning an initial group is to prevent lock
        out.
        '''
        params = {}
        params['context'] = self.context
        params['entitlementName'] = self.fixTypes(entitlementName)
        params['initialGroup'] = self.fixTypes(initialGroup)
        ret= self.runMultipart("/entitlement", "ADDENTITLEMENT", params)
        return ret['response']

    def doEntitlement_AddGroupToEntitlement(self,entitlementName,groupName):
        '''
        This method is used to add an entitlement group to an entitlement.
        '''
        params = {}
        params['context'] = self.context
        params['entitlementName'] = self.fixTypes(entitlementName)
        params['groupName'] = self.fixTypes(groupName)
        ret= self.runMultipart("/entitlement", "ADDGROUPTOENTITLEMENT", params)
        return ret['response']

    def doEntitlement_RemoveGroupFromEntitlement(self,entitlementName,groupName):
        '''
        This method reverses the act of adding a group to an entitlement.
        '''
        params = {}
        params['context'] = self.context
        params['entitlementName'] = self.fixTypes(entitlementName)
        params['groupName'] = self.fixTypes(groupName)
        ret= self.runMultipart("/entitlement", "REMOVEGROUPFROMENTITLEMENT", params)
        return ret['response']

    def doEntitlement_DeleteEntitlement(self,entitlementName):
        '''
        This method removes an entitlement entirely from the system.
        '''
        params = {}
        params['context'] = self.context
        params['entitlementName'] = self.fixTypes(entitlementName)
        ret= self.runMultipart("/entitlement", "DELETEENTITLEMENT", params)
        return ret['response']

    def doEntitlement_DeleteEntitlementGroup(self,groupName):
        '''
        This method removes an entitlement group from the system.
        '''
        params = {}
        params['context'] = self.context
        params['groupName'] = self.fixTypes(groupName)
        ret= self.runMultipart("/entitlement", "DELETEENTITLEMENTGROUP", params)
        return ret['response']

    def doEntitlement_AddEntitlementGroup(self,groupName):
        '''
        This method adds a new entitlement group to the system.
        '''
        params = {}
        params['context'] = self.context
        params['groupName'] = self.fixTypes(groupName)
        ret= self.runMultipart("/entitlement", "ADDENTITLEMENTGROUP", params)
        return ret['response']

    def doEntitlement_AddUserToEntitlementGroup(self,groupName,userName):
        '''
        This method adds a user to an existing entitlement group. The user will then have
        all of the privileges (entitlements) associated with that group.
        '''
        params = {}
        params['context'] = self.context
        params['groupName'] = self.fixTypes(groupName)
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/entitlement", "ADDUSERTOENTITLEMENTGROUP", params)
        return ret['response']

    def doEntitlement_RemoveUserFromEntitlementGroup(self,groupName,userName):
        '''
        This method reverses the act of the adding a user to a group.
        '''
        params = {}
        params['context'] = self.context
        params['groupName'] = self.fixTypes(groupName)
        params['userName'] = self.fixTypes(userName)
        ret= self.runMultipart("/entitlement", "REMOVEUSERFROMENTITLEMENTGROUP", params)
        return ret['response']

    def doEntitlement_FindEntitlementsByUser(self,username):
        '''
        Convenience method to get all the entitlements for a user
        '''
        params = {}
        params['context'] = self.context
        params['username'] = self.fixTypes(username)
        ret= self.runMultipart("/entitlement", "FINDENTITLEMENTSBYUSER", params)
        return ret['response']

    def doEntitlement_FindEntitlementsByGroup(self,groupname):
        '''
        Convenience method to get all the entitlements for a group
        '''
        params = {}
        params['context'] = self.context
        params['groupname'] = self.fixTypes(groupname)
        ret= self.runMultipart("/entitlement", "FINDENTITLEMENTSBYGROUP", params)
        return ret['response']

    def doEntitlement_FindEntitlementsBySelf(self):
        '''
        Convenience method to get all entitlements for the current user
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/entitlement", "FINDENTITLEMENTSBYSELF", params)
        return ret['response']

    def doUser_GetWhoAmI(self):
        '''
        Returns account information for the current user.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/user", "GETWHOAMI", params)
        return ret['response']

    def doUser_LogoutUser(self):
        '''
        Logs out the active user and terminates the current session.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/user", "LOGOUTUSER", params)
        return ret['response']

    def doUser_StorePreference(self,category,name,content):
        '''
        Stores application preferences for the current user.
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        params['name'] = self.fixTypes(name)
        params['content'] = self.fixTypes(content)
        ret= self.runMultipart("/user", "STOREPREFERENCE", params)
        return ret['response']

    def doUser_GetPreference(self,category,name):
        '''
        Retrieves application preferences for the current user.
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/user", "GETPREFERENCE", params)
        return ret['response']

    def doUser_RemovePreference(self,category,name):
        '''
        Removes a previously stored preference.
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/user", "REMOVEPREFERENCE", params)
        return ret['response']

    def doUser_GetPreferenceCategories(self):
        '''
        This method will list the categories of preferences available for a user.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/user", "GETPREFERENCECATEGORIES", params)
        return ret['response']

    def doUser_GetPreferencesInCategory(self,category):
        '''
        This method will list the preference documents in a category.
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        ret= self.runMultipart("/user", "GETPREFERENCESINCATEGORY", params)
        return ret['response']

    def doUser_UpdateMyDescription(self,description):
        '''
        Updates the description for the current user.
        '''
        params = {}
        params['context'] = self.context
        params['description'] = self.fixTypes(description)
        ret= self.runMultipart("/user", "UPDATEMYDESCRIPTION", params)
        return ret['response']

    def doUser_ChangeMyPassword(self,oldHashPassword,newHashPassword):
        '''
        Changes the password for the current user.
        '''
        params = {}
        params['context'] = self.context
        params['oldHashPassword'] = self.fixTypes(oldHashPassword)
        params['newHashPassword'] = self.fixTypes(newHashPassword)
        ret= self.runMultipart("/user", "CHANGEMYPASSWORD", params)
        return ret['response']

    def doUser_ChangeMyEmail(self,newAddress):
        '''
        Changes the email for the current user.
        '''
        params = {}
        params['context'] = self.context
        params['newAddress'] = self.fixTypes(newAddress)
        ret= self.runMultipart("/user", "CHANGEMYEMAIL", params)
        return ret['response']

    def doUser_GetServerApiVersion(self):
        '''
        Retrieves the API version currently in use.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/user", "GETSERVERAPIVERSION", params)
        return ret['response']

    def doUser_RunFilterCubeView(self,typeURI,scriptURI,filterParams,groupFields,columnFields):
        '''
        '''
        params = {}
        params['context'] = self.context
        params['typeURI'] = self.fixTypes(typeURI)
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['filterParams'] = self.fixTypes(filterParams)
        params['groupFields'] = self.fixTypes(groupFields)
        params['columnFields'] = self.fixTypes(columnFields)
        ret= self.runMultipart("/user", "RUNFILTERCUBEVIEW", params)
        return ret['response']

    def doUser_RunNativeQuery(self,typeURI,repoType,queryParams):
        '''
        '''
        params = {}
        params['context'] = self.context
        params['typeURI'] = self.fixTypes(typeURI)
        params['repoType'] = self.fixTypes(repoType)
        params['queryParams'] = self.fixTypes(queryParams)
        ret= self.runMultipart("/user", "RUNNATIVEQUERY", params)
        return ret['response']

    def doUser_RunNativeFilterCubeView(self,typeURI,repoType,queryParams,groupFields,columnFields):
        '''
        Very much like a filter cube view, except that the initial content is taken from
        a native query executed against a REP repository instead of running through the
        viewsub system.
        '''
        params = {}
        params['context'] = self.context
        params['typeURI'] = self.fixTypes(typeURI)
        params['repoType'] = self.fixTypes(repoType)
        params['queryParams'] = self.fixTypes(queryParams)
        params['groupFields'] = self.fixTypes(groupFields)
        params['columnFields'] = self.fixTypes(columnFields)
        ret= self.runMultipart("/user", "RUNNATIVEFILTERCUBEVIEW", params)
        return ret['response']

    def doUser_IsPermitted(self,apiCall,callParam):
        '''
        A method to check whether the current user is allowed to make the API call. Useful
        for the UI so that it can determine whether or not to show a particular item.
        '''
        params = {}
        params['context'] = self.context
        params['apiCall'] = self.fixTypes(apiCall)
        params['callParam'] = self.fixTypes(callParam)
        ret= self.runMultipart("/user", "ISPERMITTED", params)
        return ret['response']

    def doSchedule_CreateJob(self,jobURI,description,scriptURI,cronExpression,timeZone,jobParams,autoActivate):
        '''
        Creates a new job. The executableURI should point to a RaptureScript. A job needs
        to be activated for it be available for execution. A job can be either auto-activate
        (i.e. it is activated, then de-activated while it runs, then activated on completion.
        OR it can be not-auto-activate, whereupon it needs to be activatedmanually, by either
        a predecessor job (a job that has this job as a dependency) or manually via the
        activate schedule API call.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['description'] = self.fixTypes(description)
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['cronExpression'] = self.fixTypes(cronExpression)
        params['timeZone'] = self.fixTypes(timeZone)
        params['jobParams'] = self.fixTypes(jobParams)
        params['autoActivate'] = self.fixTypes(autoActivate)
        ret= self.runMultipart("/schedule", "CREATEJOB", params)
        return ret['response']

    def doSchedule_CreateWorkflowJob(self,jobURI,description,workflowURI,cronExpression,timeZone,jobParams,autoActivate,maxRuntimeMinutes,appStatusNamePattern):
        '''
        Creates a new Workflow-based job. The executableURI should point to a Workflow. A
        WorkOrder will be createdwhen the job is executed. The jobParams will be passed
        in to the Workflow as the contextMap.The maxRuntimeMinutes will be used to throw
        alerts when the job runs longer than expected.A job needs to be activated for it
        be available for execution. A job can be either auto-activate (i.e. it is activated,
        then de-activated while it runs, then activated on completion. OR it can be not-auto-activate,
        whereupon it needs to be activatedmanually, by either a predecessor job (a job that
        has this job as a dependency) or manually via the activate schedule API call.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['description'] = self.fixTypes(description)
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['cronExpression'] = self.fixTypes(cronExpression)
        params['timeZone'] = self.fixTypes(timeZone)
        params['jobParams'] = self.fixTypes(jobParams)
        params['autoActivate'] = self.fixTypes(autoActivate)
        params['maxRuntimeMinutes'] = self.fixTypes(maxRuntimeMinutes)
        params['appStatusNamePattern'] = self.fixTypes(appStatusNamePattern)
        ret= self.runMultipart("/schedule", "CREATEWORKFLOWJOB", params)
        return ret['response']

    def doSchedule_ActivateJob(self,jobURI,extraParams):
        '''
        Activate a job (usually that is not auto-activate). This means that the job will
        now be picked up by the scheduler and executed at whatever time it is configured
        to run.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['extraParams'] = self.fixTypes(extraParams)
        ret= self.runMultipart("/schedule", "ACTIVATEJOB", params)
        return ret['response']

    def doSchedule_DeactivateJob(self,jobURI):
        '''
        Turns off a job's schedule-based execution.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        ret= self.runMultipart("/schedule", "DEACTIVATEJOB", params)
        return ret['response']

    def doSchedule_RetrieveJob(self,jobURI):
        '''
        Retrieve the definition of a job given its URI.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        ret= self.runMultipart("/schedule", "RETRIEVEJOB", params)
        return ret['response']

    def doSchedule_RetrieveJobs(self,uriPrefix):
        '''
        Retrieve the definition of all jobs in the system whose uri starts with a certain
        prefix (e.g job://my/jobs/date1)
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        ret= self.runMultipart("/schedule", "RETRIEVEJOBS", params)
        return ret['response']

    def doSchedule_RunJobNow(self,jobURI,extraParams):
        '''
        Try to schedule this job to run as soon as possible.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['extraParams'] = self.fixTypes(extraParams)
        ret= self.runMultipart("/schedule", "RUNJOBNOW", params)
        return ret['response']

    def doSchedule_ResetJob(self,jobURI):
        '''
        Removes the upcoming scheduled execution of this job and schedules it to run according
        to the cron in the job configuration.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        ret= self.runMultipart("/schedule", "RESETJOB", params)
        return ret['response']

    def doSchedule_RetrieveJobExec(self,jobURI,execTime):
        '''
        Retrieves the execution of a job.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['execTime'] = self.fixTypes(execTime)
        ret= self.runMultipart("/schedule", "RETRIEVEJOBEXEC", params)
        return ret['response']

    def doSchedule_DeleteJob(self,jobURI):
        '''
        Removes a job from the system.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        ret= self.runMultipart("/schedule", "DELETEJOB", params)
        return ret['response']

    def doSchedule_GetJobs(self):
        '''
        Retrieves all of the JobURI addresses of the jobs in the system.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/schedule", "GETJOBS", params)
        return ret['response']

    def doSchedule_GetUpcomingJobs(self):
        '''
        Retrieves all of the upcoming jobs in the system.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/schedule", "GETUPCOMINGJOBS", params)
        return ret['response']

    def doSchedule_GetWorkflowExecsStatus(self):
        '''
        Retrieves the status of all current workflow-based job executions. This looks into
        the last execution as well as upcoming execution for all scheduled jobs. The return
        object contains a list of jobs that succeeded, failed, are overrun, or are ok (i.e.
        either scheduled to start in the future or currently running but not overrun). For
        failed or overrun jobs, information is also returned as to whether the failure/overrun
        has been acknowledged. See also ackJobError.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/schedule", "GETWORKFLOWEXECSSTATUS", params)
        return ret['response']

    def doSchedule_AckJobError(self,jobURI,execTime,jobErrorType):
        '''
        Acknowledges a job failure, storing the acknowledgment in Rapture. This information
        is returned when retrieving job statuses. See also getWorkflowExecsStatus.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['execTime'] = self.fixTypes(execTime)
        params['jobErrorType'] = self.fixTypes(jobErrorType)
        ret= self.runMultipart("/schedule", "ACKJOBERROR", params)
        return ret['response']

    def doSchedule_GetNextExec(self,jobURI):
        '''
        Gets the next execution time for a given job.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        ret= self.runMultipart("/schedule", "GETNEXTEXEC", params)
        return ret['response']

    def doSchedule_GetJobExecs(self,jobURI,start,count,reversed):
        '''
        Retrieves a list of job executions in a given range.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['start'] = self.fixTypes(start)
        params['count'] = self.fixTypes(count)
        params['reversed'] = self.fixTypes(reversed)
        ret= self.runMultipart("/schedule", "GETJOBEXECS", params)
        return ret['response']

    def doSchedule_BatchGetJobExecs(self,jobURI,start,count,reversed):
        '''
        Retrieve a list of job executions for a list of jobs. This will return the job executions
        starting at index start (inclusive), and going onfor count. If reverse is true,
        it starts from the end.
        '''
        params = {}
        params['context'] = self.context
        params['jobURI'] = self.fixTypes(jobURI)
        params['start'] = self.fixTypes(start)
        params['count'] = self.fixTypes(count)
        params['reversed'] = self.fixTypes(reversed)
        ret= self.runMultipart("/schedule", "BATCHGETJOBEXECS", params)
        return ret['response']

    def doSchedule_IsJobReadyToRun(self,toJobURI):
        '''
        Return whether the given job is ready to run.
        '''
        params = {}
        params['context'] = self.context
        params['toJobURI'] = self.fixTypes(toJobURI)
        ret= self.runMultipart("/schedule", "ISJOBREADYTORUN", params)
        return ret['response']

    def doSchedule_GetCurrentWeekTimeRecords(self,weekOffsetfromNow):
        '''
        For TimeServer, get a list of scheduled events for this week (starts on Sunday, use
        offset to look at next week)
        '''
        params = {}
        params['context'] = self.context
        params['weekOffsetfromNow'] = self.fixTypes(weekOffsetfromNow)
        ret= self.runMultipart("/schedule", "GETCURRENTWEEKTIMERECORDS", params)
        return ret['response']

    def doSchedule_GetCurrentDayJobs(self):
        '''
        For TimeServer, get a list of scheduled jobs for the current day
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/schedule", "GETCURRENTDAYJOBS", params)
        return ret['response']

    def doEvent_GetEvent(self,eventUri):
        '''
        This method is used to retrieve information about an event (primarily the scripts
        attached to it).
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        ret= self.runMultipart("/event", "GETEVENT", params)
        return ret['response']

    def doEvent_PutEvent(self,event):
        '''
        This method puts an event in the system.
        '''
        params = {}
        params['context'] = self.context
        params['event'] = self.fixTypes(event)
        ret= self.runMultipart("/event", "PUTEVENT", params)
        return ret['response']

    def doEvent_DeleteEvent(self,eventUri):
        '''
        This method removes an event (and any attached scripts) from the system. If the event
        is fired at a later point nothing will happen as there would be no scripts attached.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        ret= self.runMultipart("/event", "DELETEEVENT", params)
        return ret['response']

    def doEvent_ListEventsByUriPrefix(self,eventUriPrefix):
        '''
        Return a list of full display names of the paths below this one. Ideally optimized
        depending on the repo.
        '''
        params = {}
        params['context'] = self.context
        params['eventUriPrefix'] = self.fixTypes(eventUriPrefix)
        ret= self.runMultipart("/event", "LISTEVENTSBYURIPREFIX", params)
        return ret['response']

    def doEvent_AddEventScript(self,eventUri,scriptUri,performOnce):
        '''
        This method is used to attach a script to an event. A final parameter signals whether
        this script should be detached from the event when it is fired.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['scriptUri'] = self.fixTypes(scriptUri)
        params['performOnce'] = self.fixTypes(performOnce)
        ret= self.runMultipart("/event", "ADDEVENTSCRIPT", params)
        return ret['response']

    def doEvent_DeleteEventScript(self,eventUri,scriptUri):
        '''
        This method detaches a script from the event.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['scriptUri'] = self.fixTypes(scriptUri)
        ret= self.runMultipart("/event", "DELETEEVENTSCRIPT", params)
        return ret['response']

    def doEvent_AddEventMessage(self,eventUri,name,pipeline,params):
        '''
        This method is used to attach a message to an event. When the event is fired a message
        is sent to the pipeline with content based on the context of the event and parameters
        passed to this call.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['name'] = self.fixTypes(name)
        params['pipeline'] = self.fixTypes(pipeline)
        params['params'] = self.fixTypes(params)
        ret= self.runMultipart("/event", "ADDEVENTMESSAGE", params)
        return ret['response']

    def doEvent_DeleteEventMessage(self,eventUri,name):
        '''
        This method reverses the message attachment, using the same name as passed in the
        original attachMessage call
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/event", "DELETEEVENTMESSAGE", params)
        return ret['response']

    def doEvent_AddEventNotification(self,eventUri,name,notification,params):
        '''
        This method is used to attach a notification to an event. When the event is fired
        a message is sent to the notification with content based on the context of the event
        and parameters passed to this call.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['name'] = self.fixTypes(name)
        params['notification'] = self.fixTypes(notification)
        params['params'] = self.fixTypes(params)
        ret= self.runMultipart("/event", "ADDEVENTNOTIFICATION", params)
        return ret['response']

    def doEvent_DeleteEventNotification(self,eventUri,name):
        '''
        This method reverses the notification attachment, using the same name as passed in
        the original attachNotification call
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/event", "DELETEEVENTNOTIFICATION", params)
        return ret['response']

    def doEvent_AddEventWorkflow(self,eventUri,name,workflowUri,params):
        '''
        This method is used to attach a workflow (dp) to an event. When the event is fired
        an instance of the workflow   is started.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['name'] = self.fixTypes(name)
        params['workflowUri'] = self.fixTypes(workflowUri)
        params['params'] = self.fixTypes(params)
        ret= self.runMultipart("/event", "ADDEVENTWORKFLOW", params)
        return ret['response']

    def doEvent_DeleteEventWorkflow(self,eventUri,name):
        '''
        This method reverses the notification attachment, using the same name as passed in
        the original attachWorflowToEvent call.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/event", "DELETEEVENTWORKFLOW", params)
        return ret['response']

    def doEvent_RunEvent(self,eventUri,associatedUri,eventContext):
        '''
        This method fires an event, scheduling any attached scripts to run. The optional
        displayName and contextparameters are passed to the script when fired.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['associatedUri'] = self.fixTypes(associatedUri)
        params['eventContext'] = self.fixTypes(eventContext)
        ret= self.runMultipart("/event", "RUNEVENT", params)
        return ret['response']

    def doEvent_RunEventWithContext(self,eventUri,associatedUri,eventContextMap):
        '''
        This method fires an event, scheduling any attached workflows or scripts to run.
        The optional associatedURI and contextmap are passed to the event workflow when
        fired. The event's unique id is returned. This id is passed to any scripts, workflows,
        etcinvoked by the event
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        params['associatedUri'] = self.fixTypes(associatedUri)
        params['eventContextMap'] = self.fixTypes(eventContextMap)
        ret= self.runMultipart("/event", "RUNEVENTWITHCONTEXT", params)
        return ret['response']

    def doEvent_EventExists(self,eventUri):
        '''
        Determines whether an event has been defined.
        '''
        params = {}
        params['context'] = self.context
        params['eventUri'] = self.fixTypes(eventUri)
        ret= self.runMultipart("/event", "EVENTEXISTS", params)
        return ret['response']

    def doEvent_DeleteEventsByUriPrefix(self,uriPrefix):
        '''
        Removes a folder and its contents recursively, including empty subfolders. Validates
        entitlement on individual events and folders. Returns a list of the events and folders
        removed.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        ret= self.runMultipart("/event", "DELETEEVENTSBYURIPREFIX", params)
        return ret['response']

    def doAudit_Setup(self,force):
        '''
        Sets up anything needed for audit to run properly. This should be called from the
        _startup.rfx script. This call is used internally by Rapture on startup, and is
        normally called only for debugging purposes.
        '''
        params = {}
        params['context'] = self.context
        params['force'] = self.fixTypes(force)
        ret= self.runMultipart("/audit", "SETUP", params)
        return ret['response']

    def doAudit_CreateAuditLog(self,name,config):
        '''
        This method creates a new audit log, given a name and a config string. The config
        string defines the implementation to be used to store the audit entries.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/audit", "CREATEAUDITLOG", params)
        return ret['response']

    def doAudit_DoesAuditLogExist(self,logURI):
        '''
        This method checks whether an audit log exists at the specified URI. The log must
        have been created using createAuditLog.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        ret= self.runMultipart("/audit", "DOESAUDITLOGEXIST", params)
        return ret['response']

    def doAudit_GetChildren(self,prefix):
        '''
        This method searches for audit logs whose name follows the pattern prefix/anything_else/under/here,
        where prefix is the argument that is passed in.
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        ret= self.runMultipart("/audit", "GETCHILDREN", params)
        return ret['response']

    def doAudit_DeleteAuditLog(self,logURI):
        '''
        This method removes a previously created audit log.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        ret= self.runMultipart("/audit", "DELETEAUDITLOG", params)
        return ret['response']

    def doAudit_GetAuditLog(self,logURI):
        '''
        This method retrieves the config information for a previously created audit log.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        ret= self.runMultipart("/audit", "GETAUDITLOG", params)
        return ret['response']

    def doAudit_WriteAuditEntry(self,logURI,category,level,message):
        '''
        This method writes an audit entry to the audit log specified by the URI parameter.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        params['category'] = self.fixTypes(category)
        params['level'] = self.fixTypes(level)
        params['message'] = self.fixTypes(message)
        ret= self.runMultipart("/audit", "WRITEAUDITENTRY", params)
        return ret['response']

    def doAudit_WriteAuditEntryData(self,logURI,category,level,message,data):
        '''
        This method writes an audit entry to an audit log.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        params['category'] = self.fixTypes(category)
        params['level'] = self.fixTypes(level)
        params['message'] = self.fixTypes(message)
        params['data'] = self.fixTypes(data)
        ret= self.runMultipart("/audit", "WRITEAUDITENTRYDATA", params)
        return ret['response']

    def doAudit_GetRecentLogEntries(self,logURI,count):
        '''
        This method retrieves previously registered log entries, given a maximum number of
        entries to return.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        params['count'] = self.fixTypes(count)
        ret= self.runMultipart("/audit", "GETRECENTLOGENTRIES", params)
        return ret['response']

    def doAudit_GetEntriesSince(self,logURI,when):
        '''
        This method retrieves any entries since a given entry was retrieved. The date of
        this audit entry is used to determine the start point of the query.
        '''
        params = {}
        params['context'] = self.context
        params['logURI'] = self.fixTypes(logURI)
        params['when'] = self.fixTypes(when)
        ret= self.runMultipart("/audit", "GETENTRIESSINCE", params)
        return ret['response']

    def doAudit_GetRecentUserActivity(self,user,count):
        '''
        This method retrieves all of the recent API call activity (including login) performed
        by a user, given a maximum number of entries to return.  A 'count' argument of less
        than 0 will return everything available.
        '''
        params = {}
        params['context'] = self.context
        params['user'] = self.fixTypes(user)
        params['count'] = self.fixTypes(count)
        ret= self.runMultipart("/audit", "GETRECENTUSERACTIVITY", params)
        return ret['response']

    def doMailbox_PutMessage(self,messageUri,content):
        '''
        This method is used to post a message onto a category (for a authority).
        '''
        params = {}
        params['context'] = self.context
        params['messageUri'] = self.fixTypes(messageUri)
        params['content'] = self.fixTypes(content)
        ret= self.runMultipart("/mailbox", "PUTMESSAGE", params)
        return ret['response']

    def doMailbox_MoveMessage(self,messageUri,newMessageUri):
        '''
        Moves a message from one category to another.
        '''
        params = {}
        params['context'] = self.context
        params['messageUri'] = self.fixTypes(messageUri)
        params['newMessageUri'] = self.fixTypes(newMessageUri)
        ret= self.runMultipart("/mailbox", "MOVEMESSAGE", params)
        return ret['response']

    def doMailbox_CreateMailboxRepo(self,mailboxConfig,idGenConfig):
        '''
        Define the config for mailbox storage.
        '''
        params = {}
        params['context'] = self.context
        params['mailboxConfig'] = self.fixTypes(mailboxConfig)
        params['idGenConfig'] = self.fixTypes(idGenConfig)
        ret= self.runMultipart("/mailbox", "CREATEMAILBOXREPO", params)
        return ret['response']

    def doMailbox_GetMessages(self,mailboxUri):
        '''
        Retrieves all mailbox messages for a category.
        '''
        params = {}
        params['context'] = self.context
        params['mailboxUri'] = self.fixTypes(mailboxUri)
        ret= self.runMultipart("/mailbox", "GETMESSAGES", params)
        return ret['response']

    def doFields_ListFieldsByUriPrefix(self,authority,depth):
        '''
        Returns a list of URIs of all documents and folders below this point, mapping the
        URI to a RaptureFolderInfo object
        '''
        params = {}
        params['context'] = self.context
        params['authority'] = self.fixTypes(authority)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/fields", "LISTFIELDSBYURIPREFIX", params)
        return ret['response']

    def doFields_GetField(self,fieldUri):
        '''
        Retrieves the field definition.
        '''
        params = {}
        params['context'] = self.context
        params['fieldUri'] = self.fixTypes(fieldUri)
        ret= self.runMultipart("/fields", "GETFIELD", params)
        return ret['response']

    def doFields_PutField(self,field):
        '''
        Create or replace the field definition
        '''
        params = {}
        params['context'] = self.context
        params['field'] = self.fixTypes(field)
        ret= self.runMultipart("/fields", "PUTFIELD", params)
        return ret['response']

    def doFields_FieldExists(self,fieldUri):
        '''
        Check whether a field definition with the given uri exists
        '''
        params = {}
        params['context'] = self.context
        params['fieldUri'] = self.fixTypes(fieldUri)
        ret= self.runMultipart("/fields", "FIELDEXISTS", params)
        return ret['response']

    def doFields_DeleteField(self,fieldUri):
        '''
        Delete a field definition
        '''
        params = {}
        params['context'] = self.context
        params['fieldUri'] = self.fixTypes(fieldUri)
        ret= self.runMultipart("/fields", "DELETEFIELD", params)
        return ret['response']

    def doFields_GetDocumentFields(self,docURI,fields):
        '''
        Returns a list of values referenced by the fields. Note that there is not a simple
        1:1 mapping between the returned list and the list of fields supplied as a parameter.
        '''
        params = {}
        params['context'] = self.context
        params['docURI'] = self.fixTypes(docURI)
        params['fields'] = self.fixTypes(fields)
        ret= self.runMultipart("/fields", "GETDOCUMENTFIELDS", params)
        return ret['response']

    def doFields_PutDocumentAndGetDocumentFields(self,docURI,content,fields):
        '''
        Behaves similarly to getFieldsFromDocument, except that the supplied content is first
        added to the document cache, overwriting any previous values.
        '''
        params = {}
        params['context'] = self.context
        params['docURI'] = self.fixTypes(docURI)
        params['content'] = self.fixTypes(content)
        params['fields'] = self.fixTypes(fields)
        ret= self.runMultipart("/fields", "PUTDOCUMENTANDGETDOCUMENTFIELDS", params)
        return ret['response']

    def doBlob_CreateBlobRepo(self,blobRepoUri,config,metaConfig):
        '''
        Creates a repository for unstructured data.
        '''
        params = {}
        params['context'] = self.context
        params['blobRepoUri'] = self.fixTypes(blobRepoUri)
        params['config'] = self.fixTypes(config)
        params['metaConfig'] = self.fixTypes(metaConfig)
        ret= self.runMultipart("/blob", "CREATEBLOBREPO", params)
        return ret['response']

    def doBlob_GetBlobRepoConfig(self,blobRepoUri):
        '''
        Retrieves blob repository information
        '''
        params = {}
        params['context'] = self.context
        params['blobRepoUri'] = self.fixTypes(blobRepoUri)
        ret= self.runMultipart("/blob", "GETBLOBREPOCONFIG", params)
        return ret['response']

    def doBlob_GetBlobRepoConfigs(self):
        '''
        Retrieves a collection of objects that contain the configuration information for
        all the defined blob repositories.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/blob", "GETBLOBREPOCONFIGS", params)
        return ret['response']

    def doBlob_DeleteBlobRepo(self,repoUri):
        '''
        This method removes a blob Repository and its data from the Rapture system. There
        is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['repoUri'] = self.fixTypes(repoUri)
        ret= self.runMultipart("/blob", "DELETEBLOBREPO", params)
        return ret['response']

    def doBlob_BlobRepoExists(self,repoUri):
        '''
        This api call can be used to determine whether a given repo exists.
        '''
        params = {}
        params['context'] = self.context
        params['repoUri'] = self.fixTypes(repoUri)
        ret= self.runMultipart("/blob", "BLOBREPOEXISTS", params)
        return ret['response']

    def doBlob_BlobExists(self,blobUri):
        '''
        This api call can be used to determine whether a given blob exists.
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        ret= self.runMultipart("/blob", "BLOBEXISTS", params)
        return ret['response']

    def doBlob_AddBlobContent(self,blobUri,content):
        '''
        Appends to a blob.
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        params['content'] = self.fixTypes(content)
        ret= self.runMultipart("/blob", "ADDBLOBCONTENT", params)
        return ret['response']

    def doBlob_PutBlob(self,blobUri,content,contentType):
        '''
        Stores a blob in one hit, assuming a String representation. If append, adds to any
        content already existing
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        params['content'] = self.fixTypes(content)
        params['contentType'] = self.fixTypes(contentType)
        ret= self.runMultipart("/blob", "PUTBLOB", params)
        return ret['response']

    def doBlob_GetBlob(self,blobUri):
        '''
        Retrieves a blob and its metadata. The blob is represented as a byte array.
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        ret= self.runMultipart("/blob", "GETBLOB", params)
        return ret['response']

    def doBlob_DeleteBlob(self,blobUri):
        '''
        Removes a blob from the backing store. There is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        ret= self.runMultipart("/blob", "DELETEBLOB", params)
        return ret['response']

    def doBlob_GetBlobSize(self,blobUri):
        '''
        Retrieves the number of bytes in a blob.
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        ret= self.runMultipart("/blob", "GETBLOBSIZE", params)
        return ret['response']

    def doBlob_GetBlobMetaData(self,blobUri):
        '''
        Retrieves all metadata associated with a blob.
        '''
        params = {}
        params['context'] = self.context
        params['blobUri'] = self.fixTypes(blobUri)
        ret= self.runMultipart("/blob", "GETBLOBMETADATA", params)
        return ret['response']

    def doBlob_ListBlobsByUriPrefix(self,uriPrefix,depth):
        '''
        Returns full pathnames for an entire subtree as a map of the path to RFI.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/blob", "LISTBLOBSBYURIPREFIX", params)
        return ret['response']

    def doBlob_DeleteBlobsByUriPrefix(self,uriPrefix):
        '''
        Removes a folder and its contents recursively, including empty subfolders. Validates
        entitlement on individual blobs and folders. Returns a list of the blobs and folders
        removed.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        ret= self.runMultipart("/blob", "DELETEBLOBSBYURIPREFIX", params)
        return ret['response']

    def doJar_JarExists(self,jarUri):
        '''
        Indicates whether a given JAR exists.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "JAREXISTS", params)
        return ret['response']

    def doJar_PutJar(self,jarUri,jarContent):
        '''
        Stores a JAR.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        params['jarContent'] = self.fixTypes(jarContent)
        ret= self.runMultipart("/jar", "PUTJAR", params)
        return ret['response']

    def doJar_GetJar(self,jarUri):
        '''
        Retrieves a JAR and its metadata. The JAR is represented as a byte array.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "GETJAR", params)
        return ret['response']

    def doJar_DeleteJar(self,jarUri):
        '''
        Removes a JAR from the backing store. There is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "DELETEJAR", params)
        return ret['response']

    def doJar_GetJarSize(self,jarUri):
        '''
        Retrieves the number of bytes in a JAR.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "GETJARSIZE", params)
        return ret['response']

    def doJar_GetJarMetaData(self,jarUri):
        '''
        Retrieves all metadata associated with a JAR.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "GETJARMETADATA", params)
        return ret['response']

    def doJar_ListJarsByUriPrefix(self,uriPrefix,depth):
        '''
        Returns full pathnames for an entire subtree as a map of the path to RFI.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/jar", "LISTJARSBYURIPREFIX", params)
        return ret['response']

    def doJar_JarIsEnabled(self,jarUri):
        '''
        Indicates whether a given JAR is enabled on this server.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "JARISENABLED", params)
        return ret['response']

    def doJar_EnableJar(self,jarUri):
        '''
        Enables a JAR to be used on this server.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "ENABLEJAR", params)
        return ret['response']

    def doJar_DisableJar(self,jarUri):
        '''
        Disables a JAR from being used on this server.
        '''
        params = {}
        params['context'] = self.context
        params['jarUri'] = self.fixTypes(jarUri)
        ret= self.runMultipart("/jar", "DISABLEJAR", params)
        return ret['response']

    def doSheet_CreateSheetRepo(self,sheetURI,config):
        '''
        Creates a sheet repository.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/sheet", "CREATESHEETREPO", params)
        return ret['response']

    def doSheet_GetSheetRepoConfig(self,sheetURI):
        '''
        Gets the sheet repository's config metadata.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "GETSHEETREPOCONFIG", params)
        return ret['response']

    def doSheet_GetSheetRepoConfigs(self):
        '''
        Gets repository config metadata for all sheets.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/sheet", "GETSHEETREPOCONFIGS", params)
        return ret['response']

    def doSheet_CreateSheet(self,sheetURI):
        '''
        Creates an empty sheet at the given URI. If the sheet exists it is unaffected.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "CREATESHEET", params)
        return ret['response']

    def doSheet_DeleteSheet(self,sheetURI):
        '''
        Deletes a sheet and all its contents.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "DELETESHEET", params)
        return ret['response']

    def doSheet_SheetExists(self,sheetURI):
        '''
        Checks whether a sheet exists at a given URI.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "SHEETEXISTS", params)
        return ret['response']

    def doSheet_DeleteSheetRepo(self,repoURI):
        '''
        This method removes a Sheet Repository and its data from the Rapture system. There
        is no undo. It does not delete the sheets stored in the repo, so calling this while
        there are still sheets inside this repo will cause a memory leak.
        '''
        params = {}
        params['context'] = self.context
        params['repoURI'] = self.fixTypes(repoURI)
        ret= self.runMultipart("/sheet", "DELETESHEETREPO", params)
        return ret['response']

    def doSheet_SheetRepoExists(self,repoURI):
        '''
        This API call can be used to determine whether a given type exists in a given authority.
        '''
        params = {}
        params['context'] = self.context
        params['repoURI'] = self.fixTypes(repoURI)
        ret= self.runMultipart("/sheet", "SHEETREPOEXISTS", params)
        return ret['response']

    def doSheet_ListSheetsByUriPrefix(self,uriPrefix,depth):
        '''
        Return full pathnames for an entire subtree as a map of path to RFI
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/sheet", "LISTSHEETSBYURIPREFIX", params)
        return ret['response']

    def doSheet_DeleteSheetsByUriPrefix(self,uriPrefix):
        '''
        Removes a folder and its contents recursively, including empty subfolders. Returns
        a list of the sheets and folders removed.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        ret= self.runMultipart("/sheet", "DELETESHEETSBYURIPREFIX", params)
        return ret['response']

    def doSheet_SetSheetCell(self,sheetURI,row,column,value,tabId):
        '''
        Assigns the value passed to the specified cell.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['row'] = self.fixTypes(row)
        params['column'] = self.fixTypes(column)
        params['value'] = self.fixTypes(value)
        params['tabId'] = self.fixTypes(tabId)
        ret= self.runMultipart("/sheet", "SETSHEETCELL", params)
        return ret['response']

    def doSheet_SetBlock(self,sheetURI,startRow,startColumn,values,height,width,tabId):
        '''
        Sets values in bulk for a rectangle of cells. The inputs are specified as a 1-dimensional
        list, and the list is wrapped based on the width parameter.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['startRow'] = self.fixTypes(startRow)
        params['startColumn'] = self.fixTypes(startColumn)
        params['values'] = self.fixTypes(values)
        params['height'] = self.fixTypes(height)
        params['width'] = self.fixTypes(width)
        params['tabId'] = self.fixTypes(tabId)
        ret= self.runMultipart("/sheet", "SETBLOCK", params)
        return ret['response']

    def doSheet_GetSheetCell(self,sheetURI,row,column,tabId):
        '''
        Retrieves the data in a cell.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['row'] = self.fixTypes(row)
        params['column'] = self.fixTypes(column)
        params['tabId'] = self.fixTypes(tabId)
        ret= self.runMultipart("/sheet", "GETSHEETCELL", params)
        return ret['response']

    def doSheet_FindCellsByEpoch(self,sheetURI,tabId,epoch):
        '''
        Returns all the cells in a sheet. The epoch is the callers best known understanding
        as to the state of its knowledge of the sheet. Starting at 0 retrieves every cell.
        Thelatest epoch is returned in the response to this call. Once you know the epoch
        you can call this method to give the updates since thatepoch.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['tabId'] = self.fixTypes(tabId)
        params['epoch'] = self.fixTypes(epoch)
        ret= self.runMultipart("/sheet", "FINDCELLSBYEPOCH", params)
        return ret['response']

    def doSheet_GetSheetAndMeta(self,sheetURI):
        '''
        Get this sheet in a display form - filling in the blanks, and setting the format
        where appropriate, and passing a list of the formats in play. This should be sufficient
        for a client side renderer to do the necessary work with no further calls needed
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "GETSHEETANDMETA", params)
        return ret['response']

    def doSheet_ExportSheetAsPdf(self,sheetURI,blobURI):
        '''
        Renders the sheet to a PDF document, and saves the PDF as a blob in Rapture.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['blobURI'] = self.fixTypes(blobURI)
        ret= self.runMultipart("/sheet", "EXPORTSHEETASPDF", params)
        return ret['response']

    def doSheet_GetAllStyles(self,sheetURI):
        '''
        Gets all the style objects associated with this sheet. See also createStyle.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "GETALLSTYLES", params)
        return ret['response']

    def doSheet_RemoveStyle(self,sheetURI,styleName):
        '''
        Removes a style associated with this sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['styleName'] = self.fixTypes(styleName)
        ret= self.runMultipart("/sheet", "REMOVESTYLE", params)
        return ret['response']

    def doSheet_CreateStyle(self,sheetURI,style):
        '''
        Creates a style for this sheet. This can be used by GUIs when displaying the sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['style'] = self.fixTypes(style)
        ret= self.runMultipart("/sheet", "CREATESTYLE", params)
        return ret['response']

    def doSheet_GetAllScripts(self,sheetURI):
        '''
        Get all the scripts associated with this sheet. See also: createScript.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "GETALLSCRIPTS", params)
        return ret['response']

    def doSheet_RemoveScript(self,sheetURI,scriptName):
        '''
        Removes a script associated with this sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['scriptName'] = self.fixTypes(scriptName)
        ret= self.runMultipart("/sheet", "REMOVESCRIPT", params)
        return ret['response']

    def doSheet_CreateScript(self,sheetURI,scriptName,script):
        '''
        Creates a Reflex script and associates it with a given sheet. This script gets embedded
        into the sheet, i.e. it cannot be accessed as a standard Rapture script using the
        Script API's retrieveScript method. See also runScriptOnSheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['scriptName'] = self.fixTypes(scriptName)
        params['script'] = self.fixTypes(script)
        ret= self.runMultipart("/sheet", "CREATESCRIPT", params)
        return ret['response']

    def doSheet_RunScriptOnSheet(self,sheetURI,scriptName):
        '''
        Runs a script that is associated with this sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['scriptName'] = self.fixTypes(scriptName)
        ret= self.runMultipart("/sheet", "RUNSCRIPTONSHEET", params)
        return ret['response']

    def doSheet_GetSheetScript(self,sheetURI,scriptName):
        '''
        Gets a particular script associated with this sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['scriptName'] = self.fixTypes(scriptName)
        ret= self.runMultipart("/sheet", "GETSHEETSCRIPT", params)
        return ret['response']

    def doSheet_ExportSheetAsScript(self,sheetURI):
        '''
        Returns a String with Reflex code that can be used to create the entire sheet. This
        is useful if you want to clone a sheet onto a different instance of Rapture, or
        store it for installation as a feature.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "EXPORTSHEETASSCRIPT", params)
        return ret['response']

    def doSheet_GetSheetNamedSelections(self,sheetURI):
        '''
        Get all the ranges of interest that are marked on this sheet. See also: getSheetNamedSelection.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "GETSHEETNAMEDSELECTIONS", params)
        return ret['response']

    def doSheet_DeleteSheetNamedSelection(self,sheetURI,rangeName):
        '''
        Deletes a range associated with this sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['rangeName'] = self.fixTypes(rangeName)
        ret= self.runMultipart("/sheet", "DELETESHEETNAMEDSELECTION", params)
        return ret['response']

    def doSheet_CreateSheetNamedSelection(self,sheetURI,rangeName,range):
        '''
        Creates a range in the sheet. A range is a named set of sequential rows and columns.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['rangeName'] = self.fixTypes(rangeName)
        params['range'] = self.fixTypes(range)
        ret= self.runMultipart("/sheet", "CREATESHEETNAMEDSELECTION", params)
        return ret['response']

    def doSheet_GetSheetNotes(self,sheetURI):
        '''
        Get all the notes associated with this sheet. See also createSheetNote.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        ret= self.runMultipart("/sheet", "GETSHEETNOTES", params)
        return ret['response']

    def doSheet_DeleteSheetNote(self,sheetURI,noteId):
        '''
        Deletes a note associated with this sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['noteId'] = self.fixTypes(noteId)
        ret= self.runMultipart("/sheet", "DELETESHEETNOTE", params)
        return ret['response']

    def doSheet_CreateSheetNote(self,sheetURI,note):
        '''
        Adds a note to a sheet. One sheet can have multiple notes associated with it. A note
        is a text note with information about who created it and when.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['note'] = self.fixTypes(note)
        ret= self.runMultipart("/sheet", "CREATESHEETNOTE", params)
        return ret['response']

    def doSheet_CloneSheet(self,sheetURI,newSheetURI):
        '''
        Copies everything from one sheet to another. This is currently only allowed within
        sheets that have the same authority.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['newSheetURI'] = self.fixTypes(newSheetURI)
        ret= self.runMultipart("/sheet", "CLONESHEET", params)
        return ret['response']

    def doSheet_GetSheetNamedSelection(self,sheetURI,rangeName):
        '''
        Get the contents of a specified range on a sheet.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['rangeName'] = self.fixTypes(rangeName)
        ret= self.runMultipart("/sheet", "GETSHEETNAMEDSELECTION", params)
        return ret['response']

    def doSheet_DeleteSheetColumn(self,sheetURI,column):
        '''
        Deletes an entire column in the sheet, in all tabIds.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['column'] = self.fixTypes(column)
        ret= self.runMultipart("/sheet", "DELETESHEETCOLUMN", params)
        return ret['response']

    def doSheet_DeleteSheetRow(self,sheetURI,row):
        '''
        Deletes an entire row in the sheet, in all tabIds.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['row'] = self.fixTypes(row)
        ret= self.runMultipart("/sheet", "DELETESHEETROW", params)
        return ret['response']

    def doSheet_DeleteSheetCell(self,sheetURI,row,column,tabId):
        '''
        Deletes data stored in a given cell.
        '''
        params = {}
        params['context'] = self.context
        params['sheetURI'] = self.fixTypes(sheetURI)
        params['row'] = self.fixTypes(row)
        params['column'] = self.fixTypes(column)
        params['tabId'] = self.fixTypes(tabId)
        ret= self.runMultipart("/sheet", "DELETESHEETCELL", params)
        return ret['response']

    def doPlugin_GetInstalledPlugins(self):
        '''
        Lists plugins in the system.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/plugin", "GETINSTALLEDPLUGINS", params)
        return ret['response']

    def doPlugin_GetPluginManifest(self,manifestUri):
        '''
        Retrieves the manifest for a plugin.
        '''
        params = {}
        params['context'] = self.context
        params['manifestUri'] = self.fixTypes(manifestUri)
        ret= self.runMultipart("/plugin", "GETPLUGINMANIFEST", params)
        return ret['response']

    def doPlugin_RecordPlugin(self,plugin):
        '''
        Retrieves the manifest for a plugin.
        '''
        params = {}
        params['context'] = self.context
        params['plugin'] = self.fixTypes(plugin)
        ret= self.runMultipart("/plugin", "RECORDPLUGIN", params)
        return ret['response']

    def doPlugin_InstallPlugin(self,manifest,payload):
        '''
        Installs the plugin and updates the registry.
        '''
        params = {}
        params['context'] = self.context
        params['manifest'] = self.fixTypes(manifest)
        params['payload'] = self.fixTypes(payload)
        ret= self.runMultipart("/plugin", "INSTALLPLUGIN", params)
        return ret['response']

    def doPlugin_InstallPluginItem(self,pluginName,item):
        '''
        Installs a single item from a plugin to allow clients to operate in a low-memory
        environment
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['item'] = self.fixTypes(item)
        ret= self.runMultipart("/plugin", "INSTALLPLUGINITEM", params)
        return ret['response']

    def doPlugin_UninstallPlugin(self,name):
        '''
        Removes a plugin.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/plugin", "UNINSTALLPLUGIN", params)
        return ret['response']

    def doPlugin_UninstallPluginItem(self,item):
        '''
        Removes an item from a plugin.
        '''
        params = {}
        params['context'] = self.context
        params['item'] = self.fixTypes(item)
        ret= self.runMultipart("/plugin", "UNINSTALLPLUGINITEM", params)
        return ret['response']

    def doPlugin_DeletePluginManifest(self,manifestUri):
        '''
        Removes plugin Manifest but does not uninstall any referenced items.
        '''
        params = {}
        params['context'] = self.context
        params['manifestUri'] = self.fixTypes(manifestUri)
        ret= self.runMultipart("/plugin", "DELETEPLUGINMANIFEST", params)
        return ret['response']

    def doPlugin_GetPluginItem(self,uri):
        '''
        Gets the encoding for a Rapture object given its URI.
        '''
        params = {}
        params['context'] = self.context
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/plugin", "GETPLUGINITEM", params)
        return ret['response']

    def doPlugin_VerifyPlugin(self,plugin):
        '''
        Verifies that the contents of a plugin match the hashes in the manifest.
        '''
        params = {}
        params['context'] = self.context
        params['plugin'] = self.fixTypes(plugin)
        ret= self.runMultipart("/plugin", "VERIFYPLUGIN", params)
        return ret['response']

    def doPlugin_CreateManifest(self,pluginName):
        '''
        create an empty manifest on the server with version 0.0.0
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        ret= self.runMultipart("/plugin", "CREATEMANIFEST", params)
        return ret['response']

    def doPlugin_AddManifestItem(self,pluginName,uri):
        '''
        add an object on the server to a plugin manifest on the server
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/plugin", "ADDMANIFESTITEM", params)
        return ret['response']

    def doPlugin_AddManifestDataFolder(self,pluginName,uri):
        '''
        add uris within the specified docpath root. If no type is specifed in the uri, use
        all four of doc, blob, series, and sheet. Example1: //myProject/myfolder adds all
        four types. Example2: blob://myproject/myfolder adds only blobs
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/plugin", "ADDMANIFESTDATAFOLDER", params)
        return ret['response']

    def doPlugin_RemoveManifestDataFolder(self,pluginName,uri):
        '''
        remove uris within the specified path. If no type is specifed in the uri, use all
        four of doc, blob, series, and sheet.
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/plugin", "REMOVEMANIFESTDATAFOLDER", params)
        return ret['response']

    def doPlugin_SetManifestVersion(self,pluginName,version):
        '''
        refresh the MD5 checksums in the manifest and set the version for a manifest on the
        server
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['version'] = self.fixTypes(version)
        ret= self.runMultipart("/plugin", "SETMANIFESTVERSION", params)
        return ret['response']

    def doPlugin_RemoveItemFromManifest(self,pluginName,uri):
        '''
        remove an item from the manifest of a plugin on the server
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/plugin", "REMOVEITEMFROMMANIFEST", params)
        return ret['response']

    def doPlugin_ExportPlugin(self,pluginName,path):
        '''
        Export a plugin as a single blob. We pass in a parent path; the blob will be generated
        somewhere under that path, in a non-predictable location. The location is returned.
        '''
        params = {}
        params['context'] = self.context
        params['pluginName'] = self.fixTypes(pluginName)
        params['path'] = self.fixTypes(path)
        ret= self.runMultipart("/plugin", "EXPORTPLUGIN", params)
        return ret['response']

    def doPipeline_RemoveServerCategory(self,category):
        '''
        Deletes a given category.
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        ret= self.runMultipart("/pipeline", "REMOVESERVERCATEGORY", params)
        return ret['response']

    def doPipeline_GetServerCategories(self):
        '''
        List server categories.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/pipeline", "GETSERVERCATEGORIES", params)
        return ret['response']

    def doPipeline_GetBoundExchanges(self,category):
        '''
        Get bound exchanges for a category
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        ret= self.runMultipart("/pipeline", "GETBOUNDEXCHANGES", params)
        return ret['response']

    def doPipeline_DeregisterPipelineExchange(self,name):
        '''
        Removes an exchange.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/pipeline", "DEREGISTERPIPELINEEXCHANGE", params)
        return ret['response']

    def doPipeline_GetExchanges(self):
        '''
        Retrieves all registered exchanges.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/pipeline", "GETEXCHANGES", params)
        return ret['response']

    def doPipeline_GetExchange(self,name):
        '''
        Retrieves an exchange object by name.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/pipeline", "GETEXCHANGE", params)
        return ret['response']

    def doPipeline_PublishMessageToCategory(self,task):
        '''
        Publishes a message. This message will be published to the category specified in
        the RapturePipelineTask object.   If no category is specified, an error is thrown.
        This type of message should be handled by only one of   the servers belonging to
        this category; in other words, it is not a broadcast.
        '''
        params = {}
        params['context'] = self.context
        params['task'] = self.fixTypes(task)
        ret= self.runMultipart("/pipeline", "PUBLISHMESSAGETOCATEGORY", params)
        return ret['response']

    def doPipeline_BroadcastMessageToCategory(self,task):
        '''
        This message will be broadcasted to all servers belonging to the category specified
        in the RapturePipelineTaskobject. If no category is specified, an error is thrown.
        '''
        params = {}
        params['context'] = self.context
        params['task'] = self.fixTypes(task)
        ret= self.runMultipart("/pipeline", "BROADCASTMESSAGETOCATEGORY", params)
        return ret['response']

    def doPipeline_BroadcastMessageToAll(self,task):
        '''
        This message will be broadcasted to all servers connected to the pipeline system.
        '''
        params = {}
        params['context'] = self.context
        params['task'] = self.fixTypes(task)
        ret= self.runMultipart("/pipeline", "BROADCASTMESSAGETOALL", params)
        return ret['response']

    def doPipeline_GetStatus(self,taskId):
        '''
        Gets the status for a published RapturePipelineTask.
        '''
        params = {}
        params['context'] = self.context
        params['taskId'] = self.fixTypes(taskId)
        ret= self.runMultipart("/pipeline", "GETSTATUS", params)
        return ret['response']

    def doPipeline_QueryTasks(self,query):
        '''
        Queries for pipeline statuses.
        '''
        params = {}
        params['context'] = self.context
        params['query'] = self.fixTypes(query)
        ret= self.runMultipart("/pipeline", "QUERYTASKS", params)
        return ret['response']

    def doPipeline_QueryTasksOld(self,query):
        '''
        Queries for pipeline statuses.
        '''
        params = {}
        params['context'] = self.context
        params['query'] = self.fixTypes(query)
        ret= self.runMultipart("/pipeline", "QUERYTASKSOLD", params)
        return ret['response']

    def doPipeline_GetLatestTaskEpoch(self):
        '''
        On the task information, get the latest epoch (the maximum message id).
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/pipeline", "GETLATESTTASKEPOCH", params)
        return ret['response']

    def doPipeline_DrainPipeline(self,exchange):
        '''
        Drain an exchange - remove all messages.
        '''
        params = {}
        params['context'] = self.context
        params['exchange'] = self.fixTypes(exchange)
        ret= self.runMultipart("/pipeline", "DRAINPIPELINE", params)
        return ret['response']

    def doPipeline_RegisterExchangeDomain(self,domainURI,config):
        '''
        Registers a new exchange domain.
        '''
        params = {}
        params['context'] = self.context
        params['domainURI'] = self.fixTypes(domainURI)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/pipeline", "REGISTEREXCHANGEDOMAIN", params)
        return ret['response']

    def doPipeline_DeregisterExchangeDomain(self,domainURI):
        '''
        Removes an exchange domain.
        '''
        params = {}
        params['context'] = self.context
        params['domainURI'] = self.fixTypes(domainURI)
        ret= self.runMultipart("/pipeline", "DEREGISTEREXCHANGEDOMAIN", params)
        return ret['response']

    def doPipeline_GetExchangeDomains(self):
        '''
        Retrieves all registered exchange domains.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/pipeline", "GETEXCHANGEDOMAINS", params)
        return ret['response']

    def doPipeline_SetupStandardCategory(self,category):
        '''
        Sets up the default queue-exchanges and bindings for a given category.
        '''
        params = {}
        params['context'] = self.context
        params['category'] = self.fixTypes(category)
        ret= self.runMultipart("/pipeline", "SETUPSTANDARDCATEGORY", params)
        return ret['response']

    def doPipeline_MakeRPC(self,queueName,fnName,params,timeoutInSeconds):
        '''
        Make an RPC call using a pair of queues on the pipeline of the default exchange.
        I notice that the exchange is removed from the above call which seems to be a bit
        of a regression
        '''
        params = {}
        params['context'] = self.context
        params['queueName'] = self.fixTypes(queueName)
        params['fnName'] = self.fixTypes(fnName)
        params['params'] = self.fixTypes(params)
        params['timeoutInSeconds'] = self.fixTypes(timeoutInSeconds)
        ret= self.runMultipart("/pipeline", "MAKERPC", params)
        return ret['response']

    def doPipeline_CreateTopicExchange(self,domain,exchange):
        '''
        Create a topic exchange that can be used to pub/sub on
        '''
        params = {}
        params['context'] = self.context
        params['domain'] = self.fixTypes(domain)
        params['exchange'] = self.fixTypes(exchange)
        ret= self.runMultipart("/pipeline", "CREATETOPICEXCHANGE", params)
        return ret['response']

    def doPipeline_PublishTopicMessage(self,domain,exchange,topic,message):
        '''
        Publish on topic exchange (Subscription has to go low level)
        '''
        params = {}
        params['context'] = self.context
        params['domain'] = self.fixTypes(domain)
        params['exchange'] = self.fixTypes(exchange)
        params['topic'] = self.fixTypes(topic)
        params['message'] = self.fixTypes(message)
        ret= self.runMultipart("/pipeline", "PUBLISHTOPICMESSAGE", params)
        return ret['response']

    def doAsync_AsyncReflexScript(self,reflexScript,parameters):
        '''
        Run a passed script in an asynchronous manner. Tells Rapture to run the script as
        part of a predefined internal workflow,   and returns workOrderURI that can be used
        in other calls to retrieve the status. The second parameter is the set of   parameters
        that will be passed to the script upon execution.
        '''
        params = {}
        params['context'] = self.context
        params['reflexScript'] = self.fixTypes(reflexScript)
        params['parameters'] = self.fixTypes(parameters)
        ret= self.runMultipart("/async", "ASYNCREFLEXSCRIPT", params)
        return ret['response']

    def doAsync_AsyncReflexReference(self,scriptURI,parameters):
        '''
        Run a script that has already been loaded onto Rapture in an asynchronous manner.
        The script is named through its   uri. As with asyncReflexScript, the parameters
        passed in the last parameter to this function are passed   to the script upon invocation,
        and the return value from this function is a workOrderURI that can be used to determine
          the ultimate status of this WorkOrder.
        '''
        params = {}
        params['context'] = self.context
        params['scriptURI'] = self.fixTypes(scriptURI)
        params['parameters'] = self.fixTypes(parameters)
        ret= self.runMultipart("/async", "ASYNCREFLEXREFERENCE", params)
        return ret['response']

    def doAsync_AsyncStatus(self,taskId):
        '''
        Retrieve the status of a given async task. Will return null if the task id is not
        known to the environment.
        '''
        params = {}
        params['context'] = self.context
        params['taskId'] = self.fixTypes(taskId)
        ret= self.runMultipart("/async", "ASYNCSTATUS", params)
        return ret['response']

    def doAsync_SetupDefaultWorkflows(self,force):
        '''
        Sets up workflows needed to run any of these scripts. Should be called by Rapture
        internally on init
        '''
        params = {}
        params['context'] = self.context
        params['force'] = self.fixTypes(force)
        ret= self.runMultipart("/async", "SETUPDEFAULTWORKFLOWS", params)
        return ret['response']

    def doSys_RetrieveSystemConfig(self,area,path):
        '''
        Retrieve a system config
        '''
        params = {}
        params['context'] = self.context
        params['area'] = self.fixTypes(area)
        params['path'] = self.fixTypes(path)
        ret= self.runMultipart("/sys", "RETRIEVESYSTEMCONFIG", params)
        return ret['response']

    def doSys_WriteSystemConfig(self,area,path,content):
        '''
        Write a system config
        '''
        params = {}
        params['context'] = self.context
        params['area'] = self.fixTypes(area)
        params['path'] = self.fixTypes(path)
        params['content'] = self.fixTypes(content)
        ret= self.runMultipart("/sys", "WRITESYSTEMCONFIG", params)
        return ret['response']

    def doSys_RemoveSystemConfig(self,area,path):
        '''
        Remove a system document
        '''
        params = {}
        params['context'] = self.context
        params['area'] = self.fixTypes(area)
        params['path'] = self.fixTypes(path)
        ret= self.runMultipart("/sys", "REMOVESYSTEMCONFIG", params)
        return ret['response']

    def doSys_GetSystemFolders(self,area,path):
        '''
        Gets the hiearchy (the documents below this point, like with user.getChildren)
        '''
        params = {}
        params['context'] = self.context
        params['area'] = self.fixTypes(area)
        params['path'] = self.fixTypes(path)
        ret= self.runMultipart("/sys", "GETSYSTEMFOLDERS", params)
        return ret['response']

    def doSys_GetAllTopLevelRepos(self):
        '''
        Retrieve all top level repos
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/sys", "GETALLTOPLEVELREPOS", params)
        return ret['response']

    def doSys_ListByUriPrefix(self,raptureURI,marker,depth,maximum,refresh):
        '''
        Get children from the specified point.URI Cannot be null, but it can be the IndexMark
        from the ChildrenTransferObject returned by a previous call.depth indicates the
        number of levels to retrieve data for.If maximum > 0 then cap the number of entries
        returnedif refresh is false and there are more results than the defined maximum
        then store the remainder in the cache for quick access next time   If refresh is
        true and there are more results than the defined maximum then keep track of the
        values that have been returned. On the next call re-read the tree and return only
        new entries.  This is much slower than without refresh because the tree is re-read
        each time.
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['marker'] = self.fixTypes(marker)
        params['depth'] = self.fixTypes(depth)
        params['maximum'] = self.fixTypes(maximum)
        params['refresh'] = self.fixTypes(refresh)
        ret= self.runMultipart("/sys", "LISTBYURIPREFIX", params)
        return ret['response']

    def doSys_GetChildren(self,raptureURI):
        '''
        Retrieve all the immediate children of a URI
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/sys", "GETCHILDREN", params)
        return ret['response']

    def doSys_GetAllChildren(self,raptureURI,marker,maximum,refresh):
        '''
        Retrieve all the children of a URI, spanning multiple levels. The page size must
        be specified. If refresh is false and there are more results than the defined page
        size then store the remainder in the cache for quick access next time If refresh
        is true and there are more results than the defined maximum then keep track of the
        values that have been returned. On the next call re-read the tree and return only
        new entries. This is slower than without refresh because the tree is re-read each
        time.
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['marker'] = self.fixTypes(marker)
        params['maximum'] = self.fixTypes(maximum)
        params['refresh'] = self.fixTypes(refresh)
        ret= self.runMultipart("/sys", "GETALLCHILDREN", params)
        return ret['response']

    def doSys_GetFolderInfo(self,raptureURI):
        '''
        Determine whether the URI references an object, a folder, both or neither
        '''
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/sys", "GETFOLDERINFO", params)
        return ret['response']

    def doRunner_CreateServerGroup(self,name,description):
        '''
        Creates a new server group.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['description'] = self.fixTypes(description)
        ret= self.runMultipart("/runner", "CREATESERVERGROUP", params)
        return ret['response']

    def doRunner_DeleteServerGroup(self,name):
        '''
        Remove a server group (and all of its application definitions )
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "DELETESERVERGROUP", params)
        return ret['response']

    def doRunner_GetAllServerGroups(self):
        '''
        Returns all server groups defined in Rapture.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETALLSERVERGROUPS", params)
        return ret['response']

    def doRunner_GetAllApplicationDefinitions(self):
        '''
        Returns a list of all the applications defined in Rapture, which Rapture Runner knows
        about, including their versions. This is the list of applications that Rapture is
        aware of, but it does not necessarily run everything. To get a list of what will
        be running, look at getAllApplicationInstances.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETALLAPPLICATIONDEFINITIONS", params)
        return ret['response']

    def doRunner_GetAllLibraryDefinitions(self):
        '''
        Get a list of all libraries defined in Rapture. These are also known as Rapture add-ons,
        or plugins.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETALLLIBRARYDEFINITIONS", params)
        return ret['response']

    def doRunner_GetAllApplicationInstances(self):
        '''
        Retrieves all the application instances defined in Rapture. This is really the list
        of schedule entries, meaning every application-server group combination that is
        scheduled to run.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETALLAPPLICATIONINSTANCES", params)
        return ret['response']

    def doRunner_GetServerGroup(self,name):
        '''
        Retrieves a server group object, or null if no such object was found.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "GETSERVERGROUP", params)
        return ret['response']

    def doRunner_AddGroupInclusion(self,name,inclusion):
        '''
        Add a server group inclusion. An inclusion is a hostname where this server group
        should run. By default, this is set to *, which means run everywhere. Adding an
        inclusion makes it so that this server group will run only on certain servers.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['inclusion'] = self.fixTypes(inclusion)
        ret= self.runMultipart("/runner", "ADDGROUPINCLUSION", params)
        return ret['response']

    def doRunner_RemoveGroupInclusion(self,name,inclusion):
        '''
        Removes a server group inclusion. Refer to AddGroupInclusion for more details.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['inclusion'] = self.fixTypes(inclusion)
        ret= self.runMultipart("/runner", "REMOVEGROUPINCLUSION", params)
        return ret['response']

    def doRunner_AddGroupExclusion(self,name,exclusion):
        '''
        Add a server group exclusion. An exclusion is a hostname where this server group
        should not run. By default, this is set to empty, which means run on every host
        specified in inclusions. It makes more sense to add an exclusion if this server
        group has a wildcard (*) for inclusions. See also addGroupInclusion.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['exclusion'] = self.fixTypes(exclusion)
        ret= self.runMultipart("/runner", "ADDGROUPEXCLUSION", params)
        return ret['response']

    def doRunner_RemoveGroupExclusion(self,name,exclusion):
        '''
        Removes a server group exclusion. Refer to AddGroupExclusion for more details.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['exclusion'] = self.fixTypes(exclusion)
        ret= self.runMultipart("/runner", "REMOVEGROUPEXCLUSION", params)
        return ret['response']

    def doRunner_RemoveGroupEntry(self,name,entry):
        '''
        Remove an entry from either an exclusion or inclusion
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['entry'] = self.fixTypes(entry)
        ret= self.runMultipart("/runner", "REMOVEGROUPENTRY", params)
        return ret['response']

    def doRunner_CreateApplicationDefinition(self,name,ver,description):
        '''
        Creates an application definition.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['ver'] = self.fixTypes(ver)
        params['description'] = self.fixTypes(description)
        ret= self.runMultipart("/runner", "CREATEAPPLICATIONDEFINITION", params)
        return ret['response']

    def doRunner_DeleteApplicationDefinition(self,name):
        '''
        Delete an application definition (and any references in server groups)
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "DELETEAPPLICATIONDEFINITION", params)
        return ret['response']

    def doRunner_UpdateApplicationVersion(self,name,ver):
        '''
        Update a version of an application
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['ver'] = self.fixTypes(ver)
        ret= self.runMultipart("/runner", "UPDATEAPPLICATIONVERSION", params)
        return ret['response']

    def doRunner_CreateLibraryDefinition(self,name,ver,description):
        '''
        Creates an application library. See also getAllLibraryDefinitions.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['ver'] = self.fixTypes(ver)
        params['description'] = self.fixTypes(description)
        ret= self.runMultipart("/runner", "CREATELIBRARYDEFINITION", params)
        return ret['response']

    def doRunner_DeleteLibraryDefinition(self,name):
        '''
        Remove a library definition (and any references in server groups)
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "DELETELIBRARYDEFINITION", params)
        return ret['response']

    def doRunner_GetLibraryDefinition(self,name):
        '''
        Retrieve an library definition
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "GETLIBRARYDEFINITION", params)
        return ret['response']

    def doRunner_UpdateLibraryVersion(self,name,ver):
        '''
        Update a version of a library
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['ver'] = self.fixTypes(ver)
        ret= self.runMultipart("/runner", "UPDATELIBRARYVERSION", params)
        return ret['response']

    def doRunner_AddLibraryToGroup(self,serverGroup,libraryName):
        '''
        Associates a library with a server group.
        '''
        params = {}
        params['context'] = self.context
        params['serverGroup'] = self.fixTypes(serverGroup)
        params['libraryName'] = self.fixTypes(libraryName)
        ret= self.runMultipart("/runner", "ADDLIBRARYTOGROUP", params)
        return ret['response']

    def doRunner_RemoveLibraryFromGroup(self,serverGroup,libraryName):
        '''
        Remove the association between a library and a server group
        '''
        params = {}
        params['context'] = self.context
        params['serverGroup'] = self.fixTypes(serverGroup)
        params['libraryName'] = self.fixTypes(libraryName)
        ret= self.runMultipart("/runner", "REMOVELIBRARYFROMGROUP", params)
        return ret['response']

    def doRunner_CreateApplicationInstance(self,name,description,serverGroup,appName,timeRange,retryCount,parameters,apiUser):
        '''
        Adds an association between an application and a server group. This is the way to
        tell Rapture that a certain application needs to run (or be scheduled to run at
        given hours) as part of a server group.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['description'] = self.fixTypes(description)
        params['serverGroup'] = self.fixTypes(serverGroup)
        params['appName'] = self.fixTypes(appName)
        params['timeRange'] = self.fixTypes(timeRange)
        params['retryCount'] = self.fixTypes(retryCount)
        params['parameters'] = self.fixTypes(parameters)
        params['apiUser'] = self.fixTypes(apiUser)
        ret= self.runMultipart("/runner", "CREATEAPPLICATIONINSTANCE", params)
        return ret['response']

    def doRunner_RunApplication(self,appName,queueName,parameterInput,parameterOutput):
        '''
        Start a batch/single process (ultimately to replace the oneshot calls).
        '''
        params = {}
        params['context'] = self.context
        params['appName'] = self.fixTypes(appName)
        params['queueName'] = self.fixTypes(queueName)
        params['parameterInput'] = self.fixTypes(parameterInput)
        params['parameterOutput'] = self.fixTypes(parameterOutput)
        ret= self.runMultipart("/runner", "RUNAPPLICATION", params)
        return ret['response']

    def doRunner_RunCustomApplication(self,appName,queueName,parameterInput,parameterOutput,customApplicationPath):
        '''
        Start a batch/single process (ultimately to replace the oneshot calls)s.
        '''
        params = {}
        params['context'] = self.context
        params['appName'] = self.fixTypes(appName)
        params['queueName'] = self.fixTypes(queueName)
        params['parameterInput'] = self.fixTypes(parameterInput)
        params['parameterOutput'] = self.fixTypes(parameterOutput)
        params['customApplicationPath'] = self.fixTypes(customApplicationPath)
        ret= self.runMultipart("/runner", "RUNCUSTOMAPPLICATION", params)
        return ret['response']

    def doRunner_GetApplicationStatus(self,applicationStatusURI):
        '''
        Returns a status object that shows the current state of the app.
        '''
        params = {}
        params['context'] = self.context
        params['applicationStatusURI'] = self.fixTypes(applicationStatusURI)
        ret= self.runMultipart("/runner", "GETAPPLICATIONSTATUS", params)
        return ret['response']

    def doRunner_GetApplicationStatuses(self,date):
        '''
        Lists the apps that are interesting, given a QBE template (empty strings have default
        behavior).
        '''
        params = {}
        params['context'] = self.context
        params['date'] = self.fixTypes(date)
        ret= self.runMultipart("/runner", "GETAPPLICATIONSTATUSES", params)
        return ret['response']

    def doRunner_GetApplicationStatusDates(self):
        '''
        Lists the dates for which statuses exist.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETAPPLICATIONSTATUSDATES", params)
        return ret['response']

    def doRunner_ArchiveApplicationStatuses(self):
        '''
        Tidy up old status invocations
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "ARCHIVEAPPLICATIONSTATUSES", params)
        return ret['response']

    def doRunner_ChangeApplicationStatus(self,applicationStatusURI,statusCode,message):
        '''
        Update the status of an application instance.
        '''
        params = {}
        params['context'] = self.context
        params['applicationStatusURI'] = self.fixTypes(applicationStatusURI)
        params['statusCode'] = self.fixTypes(statusCode)
        params['message'] = self.fixTypes(message)
        ret= self.runMultipart("/runner", "CHANGEAPPLICATIONSTATUS", params)
        return ret['response']

    def doRunner_RecordStatusMessages(self,applicationStatusURI,messages):
        '''
        Adds messages to a running application instance.
        '''
        params = {}
        params['context'] = self.context
        params['applicationStatusURI'] = self.fixTypes(applicationStatusURI)
        params['messages'] = self.fixTypes(messages)
        ret= self.runMultipart("/runner", "RECORDSTATUSMESSAGES", params)
        return ret['response']

    def doRunner_TerminateApplication(self,applicationStatusURI,reasonMessage):
        '''
        Attempts to cancel the execution of an application.
        '''
        params = {}
        params['context'] = self.context
        params['applicationStatusURI'] = self.fixTypes(applicationStatusURI)
        params['reasonMessage'] = self.fixTypes(reasonMessage)
        ret= self.runMultipart("/runner", "TERMINATEAPPLICATION", params)
        return ret['response']

    def doRunner_DeleteApplicationInstance(self,name,serverGroup):
        '''
        Delete an application instance
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['serverGroup'] = self.fixTypes(serverGroup)
        ret= self.runMultipart("/runner", "DELETEAPPLICATIONINSTANCE", params)
        return ret['response']

    def doRunner_GetApplicationInstance(self,name,serverGroup):
        '''
        Retrieve an application instance
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['serverGroup'] = self.fixTypes(serverGroup)
        ret= self.runMultipart("/runner", "GETAPPLICATIONINSTANCE", params)
        return ret['response']

    def doRunner_UpdateStatus(self,name,serverGroup,myServer,status,finished):
        '''
        Update the status of a one shot execution, potentially marking it as finished
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['serverGroup'] = self.fixTypes(serverGroup)
        params['myServer'] = self.fixTypes(myServer)
        params['status'] = self.fixTypes(status)
        params['finished'] = self.fixTypes(finished)
        ret= self.runMultipart("/runner", "UPDATESTATUS", params)
        return ret['response']

    def doRunner_GetApplicationsForServerGroup(self,serverGroup):
        '''
        Returns a list of application instance (aka schedule) names that are configured to
        run as part of a specific server group.
        '''
        params = {}
        params['context'] = self.context
        params['serverGroup'] = self.fixTypes(serverGroup)
        ret= self.runMultipart("/runner", "GETAPPLICATIONSFORSERVERGROUP", params)
        return ret['response']

    def doRunner_GetApplicationsForServer(self,serverName):
        '''
        Returns a list of applications that should run on a specific host (aka server). Servers
        are defined in inclusions; see addGroupInclusion for more details. All applications
        that will run on a given server will be returned. Applications belonging to a server
        group that includes all servers via the * wildcard will also be returned.
        '''
        params = {}
        params['context'] = self.context
        params['serverName'] = self.fixTypes(serverName)
        ret= self.runMultipart("/runner", "GETAPPLICATIONSFORSERVER", params)
        return ret['response']

    def doRunner_GetApplicationDefinition(self,name):
        '''
        Retrieve an application definition
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "GETAPPLICATIONDEFINITION", params)
        return ret['response']

    def doRunner_SetRunnerConfig(self,name,value):
        '''
        Set a config variable available in RaptureRunner. The config variables understood
        are APPSOURCE and MODSOURCE, and they specify the location of the apps and libraries
        controlled by RaptureRunner.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        params['value'] = self.fixTypes(value)
        ret= self.runMultipart("/runner", "SETRUNNERCONFIG", params)
        return ret['response']

    def doRunner_DeleteRunnerConfig(self,name):
        '''
        Removes a variable from the Runner config.
        '''
        params = {}
        params['context'] = self.context
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "DELETERUNNERCONFIG", params)
        return ret['response']

    def doRunner_GetRunnerConfig(self):
        '''
        Returns the RaptureRunnerConfig object, which contains the values of the variables
        configured via setRunnerConfig.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETRUNNERCONFIG", params)
        return ret['response']

    def doRunner_RecordRunnerStatus(self,serverName,serverGroup,appInstance,appName,status):
        '''
        Records the status of an application instance by acquiring a lock based on the server
        name, similar to the behavior of cleanRunnerStatus and markForRestart.
        '''
        params = {}
        params['context'] = self.context
        params['serverName'] = self.fixTypes(serverName)
        params['serverGroup'] = self.fixTypes(serverGroup)
        params['appInstance'] = self.fixTypes(appInstance)
        params['appName'] = self.fixTypes(appName)
        params['status'] = self.fixTypes(status)
        ret= self.runMultipart("/runner", "RECORDRUNNERSTATUS", params)
        return ret['response']

    def doRunner_RecordInstanceCapabilities(self,serverName,instanceName,capabilities):
        '''
        Each RaptureApplicationInstance has certain capabilities associated with it. These
        could be queried by other apps if necessary (see getCapabilities). For example,
        the RaptureAPIServer has a capability to handle api calls, and it posts its api
        uri, including port, as a capability, that other apps can retrieve if they want
        to contact the api directly. This method will record capabilities for a given instance.
        '''
        params = {}
        params['context'] = self.context
        params['serverName'] = self.fixTypes(serverName)
        params['instanceName'] = self.fixTypes(instanceName)
        params['capabilities'] = self.fixTypes(capabilities)
        ret= self.runMultipart("/runner", "RECORDINSTANCECAPABILITIES", params)
        return ret['response']

    def doRunner_GetCapabilities(self,serverName,instanceNames):
        '''
        Returns the capabilities for one or more instance running on the specified host.
        See also recordInstanceCapabilities.
        '''
        params = {}
        params['context'] = self.context
        params['serverName'] = self.fixTypes(serverName)
        params['instanceNames'] = self.fixTypes(instanceNames)
        ret= self.runMultipart("/runner", "GETCAPABILITIES", params)
        return ret['response']

    def doRunner_GetRunnerServers(self):
        '''
        Gets a list of all the known server names (aka hostnames). This is determined by
        finding where a RaptureRunner is currently running or has run in the past and recorded
        a status (which has not been deleted), whether it be up or down.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/runner", "GETRUNNERSERVERS", params)
        return ret['response']

    def doRunner_GetRunnerStatus(self,serverName):
        '''
        Get a RaptureRunnerStatus object for one specific host, which is a map of the statuses
        of all instances on a specific host.
        '''
        params = {}
        params['context'] = self.context
        params['serverName'] = self.fixTypes(serverName)
        ret= self.runMultipart("/runner", "GETRUNNERSTATUS", params)
        return ret['response']

    def doRunner_CleanRunnerStatus(self,ageInMinutes):
        '''
        Cleans out old status information, older than the passed parameter in minutes. It
        acquires a lock based on the server name, same as recordRunnerStatus and markForRestart.
        '''
        params = {}
        params['context'] = self.context
        params['ageInMinutes'] = self.fixTypes(ageInMinutes)
        ret= self.runMultipart("/runner", "CLEANRUNNERSTATUS", params)
        return ret['response']

    def doRunner_MarkForRestart(self,serverName,name):
        '''
        Marks a running instance as needing reboot. If an application is not found as running
        on the specified server, nothing is done. This will not start a server that is not
        running. This acquires a lock based on the server name, same as recordRunnerStatus
        and cleanRunnerStatus.
        '''
        params = {}
        params['context'] = self.context
        params['serverName'] = self.fixTypes(serverName)
        params['name'] = self.fixTypes(name)
        ret= self.runMultipart("/runner", "MARKFORRESTART", params)
        return ret['response']

    def doSeries_CreateSeriesRepo(self,seriesRepoUri,config):
        '''
        Creates a repository for series data.
        '''
        params = {}
        params['context'] = self.context
        params['seriesRepoUri'] = self.fixTypes(seriesRepoUri)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/series", "CREATESERIESREPO", params)
        return ret['response']

    def doSeries_SeriesRepoExists(self,seriesRepoUri):
        '''
        Check for the existence of a given repository
        '''
        params = {}
        params['context'] = self.context
        params['seriesRepoUri'] = self.fixTypes(seriesRepoUri)
        ret= self.runMultipart("/series", "SERIESREPOEXISTS", params)
        return ret['response']

    def doSeries_SeriesExists(self,seriesUri):
        '''
        Check for the existence of a given series
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "SERIESEXISTS", params)
        return ret['response']

    def doSeries_GetSeriesRepoConfig(self,seriesRepoUri):
        '''
        Fetches the series repository config, or null if the repository is not found.
        '''
        params = {}
        params['context'] = self.context
        params['seriesRepoUri'] = self.fixTypes(seriesRepoUri)
        ret= self.runMultipart("/series", "GETSERIESREPOCONFIG", params)
        return ret['response']

    def doSeries_GetSeriesRepoConfigs(self):
        '''
        Fetch a list of all series repositories.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/series", "GETSERIESREPOCONFIGS", params)
        return ret['response']

    def doSeries_DeleteSeriesRepo(self,seriesRepoUri):
        '''
        This method removes a Series Repository and its data from the Rapture system. There
        is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['seriesRepoUri'] = self.fixTypes(seriesRepoUri)
        ret= self.runMultipart("/series", "DELETESERIESREPO", params)
        return ret['response']

    def doSeries_DeleteSeries(self,seriesRepoUri):
        '''
        This method removes a Series and its data from the Rapture system. There is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['seriesRepoUri'] = self.fixTypes(seriesRepoUri)
        ret= self.runMultipart("/series", "DELETESERIES", params)
        return ret['response']

    def doSeries_DeleteSeriesByUriPrefix(self,seriesUri):
        '''
        Recursively removes all series repositories that are children of the given Uri.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "DELETESERIESBYURIPREFIX", params)
        return ret['response']

    def doSeries_AddDoubleToSeries(self,seriesUri,pointKey,pointValue):
        '''
        Adds one point of floating-point data to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKey'] = self.fixTypes(pointKey)
        params['pointValue'] = self.fixTypes(pointValue)
        ret= self.runMultipart("/series", "ADDDOUBLETOSERIES", params)
        return ret['response']

    def doSeries_AddLongToSeries(self,seriesUri,pointKey,pointValue):
        '''
        Adds one point of type long to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKey'] = self.fixTypes(pointKey)
        params['pointValue'] = self.fixTypes(pointValue)
        ret= self.runMultipart("/series", "ADDLONGTOSERIES", params)
        return ret['response']

    def doSeries_AddStringToSeries(self,seriesUri,pointKey,pointValue):
        '''
        Adds one point of string data to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKey'] = self.fixTypes(pointKey)
        params['pointValue'] = self.fixTypes(pointValue)
        ret= self.runMultipart("/series", "ADDSTRINGTOSERIES", params)
        return ret['response']

    def doSeries_AddStructureToSeries(self,seriesUri,pointKey,pointValue):
        '''
        Adds one point containing a JSON-encoded structure to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKey'] = self.fixTypes(pointKey)
        params['pointValue'] = self.fixTypes(pointValue)
        ret= self.runMultipart("/series", "ADDSTRUCTURETOSERIES", params)
        return ret['response']

    def doSeries_AddDoublesToSeries(self,seriesUri,pointKeys,pointValues):
        '''
        Adds a list of points of floating-point data to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKeys'] = self.fixTypes(pointKeys)
        params['pointValues'] = self.fixTypes(pointValues)
        ret= self.runMultipart("/series", "ADDDOUBLESTOSERIES", params)
        return ret['response']

    def doSeries_AddLongsToSeries(self,seriesUri,pointKeys,pointValues):
        '''
        Adds a list of points of type long to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKeys'] = self.fixTypes(pointKeys)
        params['pointValues'] = self.fixTypes(pointValues)
        ret= self.runMultipart("/series", "ADDLONGSTOSERIES", params)
        return ret['response']

    def doSeries_AddStringsToSeries(self,seriesUri,pointKeys,pointValues):
        '''
        Adds a list of string points to a given series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKeys'] = self.fixTypes(pointKeys)
        params['pointValues'] = self.fixTypes(pointValues)
        ret= self.runMultipart("/series", "ADDSTRINGSTOSERIES", params)
        return ret['response']

    def doSeries_AddStructuresToSeries(self,seriesUri,pointKeys,pointValues):
        '''
        Adds a list of points containing JSON-encoded structures to a series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKeys'] = self.fixTypes(pointKeys)
        params['pointValues'] = self.fixTypes(pointValues)
        ret= self.runMultipart("/series", "ADDSTRUCTURESTOSERIES", params)
        return ret['response']

    def doSeries_DeletePointsFromSeriesByPointKey(self,seriesUri,pointKeys):
        '''
        Delete a list of points from a series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['pointKeys'] = self.fixTypes(pointKeys)
        ret= self.runMultipart("/series", "DELETEPOINTSFROMSERIESBYPOINTKEY", params)
        return ret['response']

    def doSeries_DeletePointsFromSeries(self,seriesUri):
        '''
        Removes all points in a series, then removes the series from the directory listing
        for its parent folder.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "DELETEPOINTSFROMSERIES", params)
        return ret['response']

    def doSeries_GetLastPoint(self,seriesUri):
        '''
        Retrieves the last point in a series.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "GETLASTPOINT", params)
        return ret['response']

    def doSeries_GetPoints(self,seriesUri):
        '''
        If the series size is less than the maximum batch size (one million points by default),
        this returns all points in a list. If the series is larger, an exception is thrown.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "GETPOINTS", params)
        return ret['response']

    def doSeries_GetPointsAfter(self,seriesUri,startColumn,maxNumber):
        '''
        Gets one page of data from a series
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSAFTER", params)
        return ret['response']

    def doSeries_GetPointsAfterReverse(self,seriesUri,startColumn,maxNumber):
        '''
        Gets one page of data and reverses the normal sort order
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSAFTERREVERSE", params)
        return ret['response']

    def doSeries_GetPointsInRange(self,seriesUri,startColumn,endColumn,maxNumber):
        '''
        Gets one page of data from a series range.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['endColumn'] = self.fixTypes(endColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSINRANGE", params)
        return ret['response']

    def doSeries_GetPointsAsDoubles(self,seriesUri):
        '''
        Gets the entire contents of a series and casts each value to type Double.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "GETPOINTSASDOUBLES", params)
        return ret['response']

    def doSeries_GetPointsAfterAsDoubles(self,seriesUri,startColumn,maxNumber):
        '''
        Gets one page of data from a series and casts each value to type Double.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSAFTERASDOUBLES", params)
        return ret['response']

    def doSeries_GetPointsInRangeAsDoubles(self,seriesUri,startColumn,endColumn,maxNumber):
        '''
        Gets one page of data from a series range and casts each value to type Double.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['endColumn'] = self.fixTypes(endColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSINRANGEASDOUBLES", params)
        return ret['response']

    def doSeries_GetPointsAsStrings(self,seriesUri):
        '''
        Gets the entire contents of a series and casts each value to type String.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        ret= self.runMultipart("/series", "GETPOINTSASSTRINGS", params)
        return ret['response']

    def doSeries_GetPointsAfterAsStrings(self,seriesUri,startColumn,maxNumber):
        '''
        Gets one page of data from a series and casts each value to type String.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSAFTERASSTRINGS", params)
        return ret['response']

    def doSeries_GetPointsInRangeAsStrings(self,seriesUri,startColumn,endColumn,maxNumber):
        '''
        Gets one page of data from a series range and casts each value to type String.
        '''
        params = {}
        params['context'] = self.context
        params['seriesUri'] = self.fixTypes(seriesUri)
        params['startColumn'] = self.fixTypes(startColumn)
        params['endColumn'] = self.fixTypes(endColumn)
        params['maxNumber'] = self.fixTypes(maxNumber)
        ret= self.runMultipart("/series", "GETPOINTSINRANGEASSTRINGS", params)
        return ret['response']

    def doSeries_RunSeriesScript(self,scriptContent,arguments):
        '''
        Executes a series function program and returns its default output.
        '''
        params = {}
        params['context'] = self.context
        params['scriptContent'] = self.fixTypes(scriptContent)
        params['arguments'] = self.fixTypes(arguments)
        ret= self.runMultipart("/series", "RUNSERIESSCRIPT", params)
        return ret['response']

    def doSeries_RunSeriesScriptQuiet(self,scriptContent,arguments):
        '''
        Executes a series function program and returns success status only.
        '''
        params = {}
        params['context'] = self.context
        params['scriptContent'] = self.fixTypes(scriptContent)
        params['arguments'] = self.fixTypes(arguments)
        ret= self.runMultipart("/series", "RUNSERIESSCRIPTQUIET", params)
        return ret['response']

    def doSeries_ListSeriesByUriPrefix(self,uriPrefix,depth):
        '''
        Returns full pathnames for an entire subtree as a map of path to RFI.
        '''
        params = {}
        params['context'] = self.context
        params['uriPrefix'] = self.fixTypes(uriPrefix)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/series", "LISTSERIESBYURIPREFIX", params)
        return ret['response']

    def doDecision_GetAllWorkflows(self):
        '''
        Returns all workflow definitions
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/decision", "GETALLWORKFLOWS", params)
        return ret['response']

    def doDecision_GetWorkflowChildren(self,workflowURI):
        '''
        Returns a list of full display names of the paths below this one. Ideally optimized
        depending on the repo.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        ret= self.runMultipart("/decision", "GETWORKFLOWCHILDREN", params)
        return ret['response']

    def doDecision_GetWorkOrderChildren(self,parentPath):
        '''
        Return a list of full display names of the paths below this one. Ideally optimized
        depending on the repo.
        '''
        params = {}
        params['context'] = self.context
        params['parentPath'] = self.fixTypes(parentPath)
        ret= self.runMultipart("/decision", "GETWORKORDERCHILDREN", params)
        return ret['response']

    def doDecision_PutWorkflow(self,workflow):
        '''
        Create or update a workflow to contain only the specified nodes and transitions.
        '''
        params = {}
        params['context'] = self.context
        params['workflow'] = self.fixTypes(workflow)
        ret= self.runMultipart("/decision", "PUTWORKFLOW", params)
        return ret['response']

    def doDecision_GetWorkflow(self,workflowURI):
        '''
        Returns a workflow definition, or null if not found.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        ret= self.runMultipart("/decision", "GETWORKFLOW", params)
        return ret['response']

    def doDecision_GetWorkflowStep(self,stepURI):
        '''
        Returns a step definition, or null if not found
        '''
        params = {}
        params['context'] = self.context
        params['stepURI'] = self.fixTypes(stepURI)
        ret= self.runMultipart("/decision", "GETWORKFLOWSTEP", params)
        return ret['response']

    def doDecision_GetStepCategory(self,stepURI):
        '''
        Gets the category associated with a step. This is the step's own categoryOverride,
        if present, or otherwise the category associated with the entire workflow.
        '''
        params = {}
        params['context'] = self.context
        params['stepURI'] = self.fixTypes(stepURI)
        ret= self.runMultipart("/decision", "GETSTEPCATEGORY", params)
        return ret['response']

    def doDecision_AddStep(self,workflowURI,step):
        '''
        Adds a new step to an existing workflow initially containing the specified transitions
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['step'] = self.fixTypes(step)
        ret= self.runMultipart("/decision", "ADDSTEP", params)
        return ret['response']

    def doDecision_RemoveStep(self,workflowURI,stepName):
        '''
        Removes a step from a workflow.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['stepName'] = self.fixTypes(stepName)
        ret= self.runMultipart("/decision", "REMOVESTEP", params)
        return ret['response']

    def doDecision_AddTransition(self,workflowURI,stepName,transition):
        '''
        Adds a new Transition to a workflow.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['stepName'] = self.fixTypes(stepName)
        params['transition'] = self.fixTypes(transition)
        ret= self.runMultipart("/decision", "ADDTRANSITION", params)
        return ret['response']

    def doDecision_RemoveTransition(self,workflowURI,stepName,transitionName):
        '''
        Removes a transition from a workflow.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['stepName'] = self.fixTypes(stepName)
        params['transitionName'] = self.fixTypes(transitionName)
        ret= self.runMultipart("/decision", "REMOVETRANSITION", params)
        return ret['response']

    def doDecision_DeleteWorkflow(self,workflowURI):
        '''
        Deletes a workflow.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        ret= self.runMultipart("/decision", "DELETEWORKFLOW", params)
        return ret['response']

    def doDecision_CreateWorkOrder(self,workflowURI,argsMap):
        '''
        Creates and executes a workflow. If there is a defaultAppStatusUriPattern set for
        this Workflow then it will be used for the appstatus URI.Otherwise, no appstatus
        will be created.TODO make workOrderURI format align with permission checks.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['argsMap'] = self.fixTypes(argsMap)
        ret= self.runMultipart("/decision", "CREATEWORKORDER", params)
        return ret['response']

    def doDecision_CreateWorkOrderP(self,workflowURI,argsMap,appStatusUriPattern):
        '''
        Creates and executes a workflow. Same as createWorkOrder, but the appStatusUriPattern
        is passed as an explicit argument instead of using the default appStatusUriPattern
        (if one has been set).Note that the app status allows the Workflow and its output
        to be accessed via the web interface; workflows without an app status are not accessible
        in this way.
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['argsMap'] = self.fixTypes(argsMap)
        params['appStatusUriPattern'] = self.fixTypes(appStatusUriPattern)
        ret= self.runMultipart("/decision", "CREATEWORKORDERP", params)
        return ret['response']

    def doDecision_ReleaseWorkOrderLock(self,workOrderURI):
        '''
        Releases the lock associated with this WorkOrder. This method should only be used
        by admins, in case therewas an unexpected problem that caused a WorkOrder to finish
        or die without releasing the lock.
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "RELEASEWORKORDERLOCK", params)
        return ret['response']

    def doDecision_GetWorkOrderStatus(self,workOrderURI):
        '''
        Gets the status of a workOrder
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "GETWORKORDERSTATUS", params)
        return ret['response']

    def doDecision_WriteWorkflowAuditEntry(self,workOrderURI,message,error):
        '''
        Writes an audit entry related to a workOrder. Messages may be INFO or ERROR based
        on the boolean fourth parameter
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        params['message'] = self.fixTypes(message)
        params['error'] = self.fixTypes(error)
        ret= self.runMultipart("/decision", "WRITEWORKFLOWAUDITENTRY", params)
        return ret['response']

    def doDecision_GetWorkOrdersByDay(self,startTimeInstant):
        '''
        Gets the WorkOrder objects starting on a given day. Orders that carried over from
        the previous day are not included.
        '''
        params = {}
        params['context'] = self.context
        params['startTimeInstant'] = self.fixTypes(startTimeInstant)
        ret= self.runMultipart("/decision", "GETWORKORDERSBYDAY", params)
        return ret['response']

    def doDecision_GetWorkOrder(self,workOrderURI):
        '''
        Gets the top-level status object associated with the work order
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "GETWORKORDER", params)
        return ret['response']

    def doDecision_GetWorker(self,workOrderURI,workerId):
        '''
        Get the worker
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        params['workerId'] = self.fixTypes(workerId)
        ret= self.runMultipart("/decision", "GETWORKER", params)
        return ret['response']

    def doDecision_CancelWorkOrder(self,workOrderURI):
        '''
        Requests cancellation of a work order. This method returns immediately once the cancellation
        is recorded, but the individual workers may continue for some time before stopping,
        depending on the type of step being executed.
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "CANCELWORKORDER", params)
        return ret['response']

    def doDecision_ResumeWorkOrder(self,workOrderURI,resumeStepURI):
        '''
        Resume work order
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        params['resumeStepURI'] = self.fixTypes(resumeStepURI)
        ret= self.runMultipart("/decision", "RESUMEWORKORDER", params)
        return ret['response']

    def doDecision_WasCancelCalled(self,workOrderURI):
        '''
        Returns true if CancelWorkOrder was called.
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "WASCANCELCALLED", params)
        return ret['response']

    def doDecision_GetCancellationDetails(self,workOrderURI):
        '''
        Gets details for the cancellation for a workOrder -- or null if not cancelled.
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "GETCANCELLATIONDETAILS", params)
        return ret['response']

    def doDecision_GetWorkOrderDebug(self,workOrderURI):
        '''
        Gets the detailed context information for a work order in progress
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "GETWORKORDERDEBUG", params)
        return ret['response']

    def doDecision_SetWorkOrderIdGenConfig(self,config,force):
        '''
        Defines the IdGen config for work order items.
        '''
        params = {}
        params['context'] = self.context
        params['config'] = self.fixTypes(config)
        params['force'] = self.fixTypes(force)
        ret= self.runMultipart("/decision", "SETWORKORDERIDGENCONFIG", params)
        return ret['response']

    def doDecision_SetContextLiteral(self,workerURI,varAlias,literalValue):
        '''
        Sets a literal in the context. The literal value that is stored will be returned
        after a read. The workerURI is a workOrderURI with the element set to the worker
        ID.
        '''
        params = {}
        params['context'] = self.context
        params['workerURI'] = self.fixTypes(workerURI)
        params['varAlias'] = self.fixTypes(varAlias)
        params['literalValue'] = self.fixTypes(literalValue)
        ret= self.runMultipart("/decision", "SETCONTEXTLITERAL", params)
        return ret['response']

    def doDecision_SetContextLink(self,workerURI,varAlias,expressionValue):
        '''
        Set a literal in the context. This means that whatever is stored will be evaluated
        before being returned, so it must be a valid expression. The workerURI is a workOrderURI
        with the element set to the worker id
        '''
        params = {}
        params['context'] = self.context
        params['workerURI'] = self.fixTypes(workerURI)
        params['varAlias'] = self.fixTypes(varAlias)
        params['expressionValue'] = self.fixTypes(expressionValue)
        ret= self.runMultipart("/decision", "SETCONTEXTLINK", params)
        return ret['response']

    def doDecision_GetContextValue(self,workerURI,varAlias):
        '''
        Gets a value in the context, as json. The workerURI is a workOrderURI with the element
        set to the worker id.
        '''
        params = {}
        params['context'] = self.context
        params['workerURI'] = self.fixTypes(workerURI)
        params['varAlias'] = self.fixTypes(varAlias)
        ret= self.runMultipart("/decision", "GETCONTEXTVALUE", params)
        return ret['response']

    def doDecision_AddErrorToContext(self,workerURI,errorWrapper):
        '''
        Adds an error to the context of a particular worker. The workerURI is a workOrderURI
        with the element set to the worker id
        '''
        params = {}
        params['context'] = self.context
        params['workerURI'] = self.fixTypes(workerURI)
        params['errorWrapper'] = self.fixTypes(errorWrapper)
        ret= self.runMultipart("/decision", "ADDERRORTOCONTEXT", params)
        return ret['response']

    def doDecision_GetErrorsFromContext(self,workerURI):
        '''
        Gets the errors from the context for a given worker. The workerURI is a workOrderURI
        with the element set to the worker id.
        '''
        params = {}
        params['context'] = self.context
        params['workerURI'] = self.fixTypes(workerURI)
        ret= self.runMultipart("/decision", "GETERRORSFROMCONTEXT", params)
        return ret['response']

    def doDecision_GetExceptionInfo(self,workOrderURI):
        '''
        Get info about any exception(s) thrown during execution of this workorder
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        ret= self.runMultipart("/decision", "GETEXCEPTIONINFO", params)
        return ret['response']

    def doDecision_ReportStepProgress(self,workerURI,stepStartTime,message,progress,max):
        '''
        Report status of the step - workerURI: the uri of this WorkOrder with the element
        set to the worker ID - stepStartTime: the time when the step being reported started
        - message: a human-friendly message to display - progress: how many units are currently
        complete - max: how many units in total would mark this as done
        '''
        params = {}
        params['context'] = self.context
        params['workerURI'] = self.fixTypes(workerURI)
        params['stepStartTime'] = self.fixTypes(stepStartTime)
        params['message'] = self.fixTypes(message)
        params['progress'] = self.fixTypes(progress)
        params['max'] = self.fixTypes(max)
        ret= self.runMultipart("/decision", "REPORTSTEPPROGRESS", params)
        return ret['response']

    def doDecision_GetAppStatuses(self,prefix):
        '''
        Gets app statuses by prefix.
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        ret= self.runMultipart("/decision", "GETAPPSTATUSES", params)
        return ret['response']

    def doDecision_GetAppStatusDetails(self,prefix,extraContextValues):
        '''
        Gets detailed app status info by prefix. Also returns any context values requested
        in the second argument.
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        params['extraContextValues'] = self.fixTypes(extraContextValues)
        ret= self.runMultipart("/decision", "GETAPPSTATUSDETAILS", params)
        return ret['response']

    def doDecision_GetMonthlyMetrics(self,workflowURI,jobURI,argsHashValue,state):
        '''
        Get any defined average runtimes for the past month for a workflow
        '''
        params = {}
        params['context'] = self.context
        params['workflowURI'] = self.fixTypes(workflowURI)
        params['jobURI'] = self.fixTypes(jobURI)
        params['argsHashValue'] = self.fixTypes(argsHashValue)
        params['state'] = self.fixTypes(state)
        ret= self.runMultipart("/decision", "GETMONTHLYMETRICS", params)
        return ret['response']

    def doDecision_QueryLogs(self,workOrderURI,startTime,endTime,keepAlive,bufferSize,nextBatchId,stepName,stepStartTime):
        '''
        Get log messages for a workflow. Note: logs get deleted after a certain number of
        days, so this only retrieves any log messages that are within theconfigured log
        retention period. If the retention period is before the startTime, an empty response
        is returned.workOrderURI: requiredstartTime: requiredendTime: requiredkeepAlive:
        required, milliseconds to keep alive the batch, max 30000bufferSize: required, max
        100nextBatchId: optional, if null start from beginningstepName: optionalstepStartTime:
        optional, this is a timestamp in a string because of a limitation in Rapture where
        int or long arguments cannot be null
        '''
        params = {}
        params['context'] = self.context
        params['workOrderURI'] = self.fixTypes(workOrderURI)
        params['startTime'] = self.fixTypes(startTime)
        params['endTime'] = self.fixTypes(endTime)
        params['keepAlive'] = self.fixTypes(keepAlive)
        params['bufferSize'] = self.fixTypes(bufferSize)
        params['nextBatchId'] = self.fixTypes(nextBatchId)
        params['stepName'] = self.fixTypes(stepName)
        params['stepStartTime'] = self.fixTypes(stepStartTime)
        ret= self.runMultipart("/decision", "QUERYLOGS", params)
        return ret['response']

    def doRepo_GetContent(self,raptureURI):
        '''
        @Deprecated: The Repo API is being eliminated 
        Retrieve the content given a documentURI
        '''
        warnings.warn(
           'doRepo_GetContent The Repo API is being eliminated',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        ret= self.runMultipart("/repo", "GETCONTENT", params)
        return ret['response']

    def doRepo_PutContent(self,raptureURI,content,comment):
        '''
        @Deprecated: The Repo API is being eliminated 
        Store the content supplied at the document URI given. Existing content will be overwritten
        at this URI, but the previous version may be stored if the underlying repository
        supports it
        '''
        warnings.warn(
           'doRepo_PutContent The Repo API is being eliminated',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['content'] = self.fixTypes(content)
        params['comment'] = self.fixTypes(comment)
        ret= self.runMultipart("/repo", "PUTCONTENT", params)
        return ret['response']

    def doRepo_DeleteContent(self,raptureURI,comment):
        '''
        @Deprecated: The Repo API is being eliminated 
        Remove a document from the system.
        '''
        warnings.warn(
           'doRepo_DeleteContent The Repo API is being eliminated',
           DeprecationWarning
        ) 
        params = {}
        params['context'] = self.context
        params['raptureURI'] = self.fixTypes(raptureURI)
        params['comment'] = self.fixTypes(comment)
        ret= self.runMultipart("/repo", "DELETECONTENT", params)
        return ret['response']

    def doDoc_ValidateDocRepo(self,docRepoUri):
        '''
        Validates repository; requires write permission because it can cause files/tables
        to be created on first use.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "VALIDATEDOCREPO", params)
        return ret['response']

    def doDoc_CreateDocRepo(self,docRepoUri,config):
        '''
        A DocumentRepository is used to store JSON docs. This method creates and configures
        the repository for an authority.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/doc", "CREATEDOCREPO", params)
        return ret['response']

    def doDoc_DocRepoExists(self,docRepoUri):
        '''
        This API call can be used to determine whether a given repository exists.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "DOCREPOEXISTS", params)
        return ret['response']

    def doDoc_DocExists(self,docUri):
        '''
        This api call can be used to determine whether a given type exists in a given authority.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "DOCEXISTS", params)
        return ret['response']

    def doDoc_GetDocRepoConfig(self,docRepoUri):
        '''
        Retrieves the configuration string for the given document repository.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "GETDOCREPOCONFIG", params)
        return ret['response']

    def doDoc_GetDocRepoStatus(self,docRepoUri):
        '''
        Gets any available information about a repository.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "GETDOCREPOSTATUS", params)
        return ret['response']

    def doDoc_GetDocRepoConfigs(self):
        '''
        Retrieves document repositories
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/doc", "GETDOCREPOCONFIGS", params)
        return ret['response']

    def doDoc_DeleteDocRepo(self,docRepoUri):
        '''
        This method removes a documentRepository and its data from the Rapture system. There
        is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "DELETEDOCREPO", params)
        return ret['response']

    def doDoc_ArchiveRepoDocs(self,docRepoUri,versionLimit,timeLimit,ensureVersionLimit):
        '''
        This method archives older versions of a documentRepository.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        params['versionLimit'] = self.fixTypes(versionLimit)
        params['timeLimit'] = self.fixTypes(timeLimit)
        params['ensureVersionLimit'] = self.fixTypes(ensureVersionLimit)
        ret= self.runMultipart("/doc", "ARCHIVEREPODOCS", params)
        return ret['response']

    def doDoc_GetDocAndMeta(self,docUri):
        '''
        Retrieves the content and the meta data associated with a document, including version
        and user information. If the storagedoes not support metadata, this method returns
        a dummy object.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "GETDOCANDMETA", params)
        return ret['response']

    def doDoc_GetDocMeta(self,docUri):
        '''
        Retrieves only the meta data associated with a document, including version and user
        information. If the storage does notsupport metadata, this method returns a dummy
        object.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "GETDOCMETA", params)
        return ret['response']

    def doDoc_RevertDoc(self,docUri):
        '''
        Reverts this document back to the previous version by taking the previous version
        and making a new version.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "REVERTDOC", params)
        return ret['response']

    def doDoc_GetDoc(self,docUri):
        '''
        Retrieves the content of a document.

        Arguments: 
        docUri -- a string of characters used to identify a document
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "GETDOC", params)
        return ret['response']

    def doDoc_PutDoc(self,docUri,content):
        '''
        Stores a document in the Rapture system.

        Arguments: 
        docUri -- a string of characters used to identify a document
        content -- the information to be stored within the document
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        params['content'] = self.fixTypes(content)
        ret= self.runMultipart("/doc", "PUTDOC", params)
        return ret['response']

    def doDoc_PutDocWithVersion(self,docUri,content,currentVersion):
        '''
        Attempts to put the content into the repository, but fails if the repository supports
        versioning and the current version ofthe document stored does not match the version
        passed. A version of zero implies that the document should not exist. The purposeof
        this call is for a client to be able to call getDocAndMeta to retrieve an existing
        document, modify it, and save the contentback, using the version number in the metadata
        of the document. If another client has modified the data since it was loaded, thiscall
        will return false, indicating that the save was not possible.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        params['content'] = self.fixTypes(content)
        params['currentVersion'] = self.fixTypes(currentVersion)
        ret= self.runMultipart("/doc", "PUTDOCWITHVERSION", params)
        return ret['response']

    def doDoc_PutDocWithEventContext(self,docUri,content,eventContext):
        '''
        Store a document in the Rapture system, passing in an event context to be added to
        any events spawned off by this put. Parts ofthe uri could be automatically generated
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        params['content'] = self.fixTypes(content)
        params['eventContext'] = self.fixTypes(eventContext)
        ret= self.runMultipart("/doc", "PUTDOCWITHEVENTCONTEXT", params)
        return ret['response']

    def doDoc_DeleteDoc(self,docUri):
        '''
        Removes a document attribute. Can be used to remove all attributes for a given type
        as well if the key argument is null.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "DELETEDOC", params)
        return ret['response']

    def doDoc_RenameDoc(self,fromDocUri,toDocUri):
        '''
        Renames a document, by getting and putting it on the system without transferring
        the data back to the client.
        '''
        params = {}
        params['context'] = self.context
        params['fromDocUri'] = self.fixTypes(fromDocUri)
        params['toDocUri'] = self.fixTypes(toDocUri)
        ret= self.runMultipart("/doc", "RENAMEDOC", params)
        return ret['response']

    def doDoc_GetDocs(self,docUris):
        '''
        Returns a map of contents where the key is the normalized input Uri and the value
        is the document retrieved
        '''
        params = {}
        params['context'] = self.context
        params['docUris'] = self.fixTypes(docUris)
        ret= self.runMultipart("/doc", "GETDOCS", params)
        return ret['response']

    def doDoc_GetDocAndMetas(self,docUris):
        '''
        Returns a list of documents and their associated meta data - the meta data includes
        version and user information
        '''
        params = {}
        params['context'] = self.context
        params['docUris'] = self.fixTypes(docUris)
        ret= self.runMultipart("/doc", "GETDOCANDMETAS", params)
        return ret['response']

    def doDoc_DocsExist(self,docUris):
        '''
        Returns a list of true/false statements on whether the listed Uris refer to a valid
        document. Note: a folder is not considered tobe a document.
        '''
        params = {}
        params['context'] = self.context
        params['docUris'] = self.fixTypes(docUris)
        ret= self.runMultipart("/doc", "DOCSEXIST", params)
        return ret['response']

    def doDoc_PutDocs(self,docUris,contents):
        '''
        Put a series of documents in a batch form. Refer to putDoc for details.
        '''
        params = {}
        params['context'] = self.context
        params['docUris'] = self.fixTypes(docUris)
        params['contents'] = self.fixTypes(contents)
        ret= self.runMultipart("/doc", "PUTDOCS", params)
        return ret['response']

    def doDoc_RenameDocs(self,authority,comment,fromDocUris,toDocUris):
        '''
        Renames a series of documents in batch form. See renameDoc.
        '''
        params = {}
        params['context'] = self.context
        params['authority'] = self.fixTypes(authority)
        params['comment'] = self.fixTypes(comment)
        params['fromDocUris'] = self.fixTypes(fromDocUris)
        params['toDocUris'] = self.fixTypes(toDocUris)
        ret= self.runMultipart("/doc", "RENAMEDOCS", params)
        return ret['response']

    def doDoc_DeleteDocsByUriPrefix(self,docUri):
        '''
        Removes a folder and its contents recursively, including empty subfolders. Validates
        entitlement on individual docs and folders. Returns a list of the documents and
        folders removed.
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        ret= self.runMultipart("/doc", "DELETEDOCSBYURIPREFIX", params)
        return ret['response']

    def doDoc_ListDocsByUriPrefix(self,docUri,depth):
        '''
        Returns a list of Uris of all documents and folders below this point, mapping the
        Uri to a RaptureFolderInfo object
        '''
        params = {}
        params['context'] = self.context
        params['docUri'] = self.fixTypes(docUri)
        params['depth'] = self.fixTypes(depth)
        ret= self.runMultipart("/doc", "LISTDOCSBYURIPREFIX", params)
        return ret['response']

    def doDoc_SetDocAttribute(self,attributeUri,value):
        '''
        Adds a single attribute to an existing document.
        '''
        params = {}
        params['context'] = self.context
        params['attributeUri'] = self.fixTypes(attributeUri)
        params['value'] = self.fixTypes(value)
        ret= self.runMultipart("/doc", "SETDOCATTRIBUTE", params)
        return ret['response']

    def doDoc_SetDocAttributes(self,attributeUri,keys,values):
        '''
        Adds attributes to an existing document in key/value pairs.
        '''
        params = {}
        params['context'] = self.context
        params['attributeUri'] = self.fixTypes(attributeUri)
        params['keys'] = self.fixTypes(keys)
        params['values'] = self.fixTypes(values)
        ret= self.runMultipart("/doc", "SETDOCATTRIBUTES", params)
        return ret['response']

    def doDoc_GetDocAttribute(self,attributeUri):
        '''
        Get a single attribute for the given uri, attributeType, and key e.g. displayName/$attributeType/key
        '''
        params = {}
        params['context'] = self.context
        params['attributeUri'] = self.fixTypes(attributeUri)
        ret= self.runMultipart("/doc", "GETDOCATTRIBUTE", params)
        return ret['response']

    def doDoc_GetDocAttributes(self,attributeUri):
        '''
        Gets all known attributes for the given uri e.g. displayName/$attributeType
        '''
        params = {}
        params['context'] = self.context
        params['attributeUri'] = self.fixTypes(attributeUri)
        ret= self.runMultipart("/doc", "GETDOCATTRIBUTES", params)
        return ret['response']

    def doDoc_DeleteDocAttribute(self,attributeUri):
        '''
        Removes a document attribute.  Can be used to remove all attributes for a given type
        as well if key argument is null.
        '''
        params = {}
        params['context'] = self.context
        params['attributeUri'] = self.fixTypes(attributeUri)
        ret= self.runMultipart("/doc", "DELETEDOCATTRIBUTE", params)
        return ret['response']

    def doDoc_GetDocRepoIdGenUri(self,docRepoUri):
        '''
        Returns the Uri that's associated with the idgen that belongs to this document repository.
        Note that every repository has aidgen Uri, even if no idgen is attached to it.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "GETDOCREPOIDGENURI", params)
        return ret['response']

    def doDoc_SetDocRepoIdGenConfig(self,docRepoUri,idGenConfig):
        '''
        This method creates a idgen and attaches it to a document repository. This way, when
        a document containing an autoid stringis created that autoid will be replaced with
        a unique id.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        params['idGenConfig'] = self.fixTypes(idGenConfig)
        ret= self.runMultipart("/doc", "SETDOCREPOIDGENCONFIG", params)
        return ret['response']

    def doDoc_GetDocRepoIdGenConfig(self,docRepoUri):
        '''
        This method returns any idgen associated with this doc repo, or null if there isn't
        one.
        '''
        params = {}
        params['context'] = self.context
        params['docRepoUri'] = self.fixTypes(docRepoUri)
        ret= self.runMultipart("/doc", "GETDOCREPOIDGENCONFIG", params)
        return ret['response']

    def doRelationship_CreateRelationshipRepo(self,relationshipRepoURI,config):
        '''
        Creates a repository in which to store relationship information.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipRepoURI'] = self.fixTypes(relationshipRepoURI)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/relationship", "CREATERELATIONSHIPREPO", params)
        return ret['response']

    def doRelationship_GetRelationshipRepoConfig(self,blobRepoURI):
        '''
        Retrieves blob repository information
        '''
        params = {}
        params['context'] = self.context
        params['blobRepoURI'] = self.fixTypes(blobRepoURI)
        ret= self.runMultipart("/relationship", "GETRELATIONSHIPREPOCONFIG", params)
        return ret['response']

    def doRelationship_GetAllRelationshipRepoConfigs(self):
        '''
        Retrieves relationship repository configurations.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/relationship", "GETALLRELATIONSHIPREPOCONFIGS", params)
        return ret['response']

    def doRelationship_DeleteRelationshipRepo(self,repoURI):
        '''
        This method removes a Relationship Repository and its data from the Rapture system.
        There is no undo.
        '''
        params = {}
        params['context'] = self.context
        params['repoURI'] = self.fixTypes(repoURI)
        ret= self.runMultipart("/relationship", "DELETERELATIONSHIPREPO", params)
        return ret['response']

    def doRelationship_DoesRelationshipRepoExist(self,repoURI):
        '''
        This api call can be used to determine whether a given repo exists.
        '''
        params = {}
        params['context'] = self.context
        params['repoURI'] = self.fixTypes(repoURI)
        ret= self.runMultipart("/relationship", "DOESRELATIONSHIPREPOEXIST", params)
        return ret['response']

    def doRelationship_DoesRelationshipExist(self,relationshipURI):
        '''
        This API call can be used to determine whether a given relationship type exists in
        a given authority.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipURI'] = self.fixTypes(relationshipURI)
        ret= self.runMultipart("/relationship", "DOESRELATIONSHIPEXIST", params)
        return ret['response']

    def doRelationship_CreateRelationship(self,relationshipAuthorityURI,fromURI,toURI,label,properties):
        '''
        Stores a relationship link and returns its URI.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipAuthorityURI'] = self.fixTypes(relationshipAuthorityURI)
        params['fromURI'] = self.fixTypes(fromURI)
        params['toURI'] = self.fixTypes(toURI)
        params['label'] = self.fixTypes(label)
        params['properties'] = self.fixTypes(properties)
        ret= self.runMultipart("/relationship", "CREATERELATIONSHIP", params)
        return ret['response']

    def doRelationship_GetRelationship(self,relationshipURI):
        '''
        Retrieves a relationship link.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipURI'] = self.fixTypes(relationshipURI)
        ret= self.runMultipart("/relationship", "GETRELATIONSHIP", params)
        return ret['response']

    def doRelationship_DeleteRelationship(self,relationshipURI):
        '''
        Deletes a relationship link.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipURI'] = self.fixTypes(relationshipURI)
        ret= self.runMultipart("/relationship", "DELETERELATIONSHIP", params)
        return ret['response']

    def doRelationship_GetOutboundRelationships(self,relationshipRepoURI,fromURI):
        '''
        Gets all the relationship links with the specified Rapture resource as the "from"
        half of the link.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipRepoURI'] = self.fixTypes(relationshipRepoURI)
        params['fromURI'] = self.fixTypes(fromURI)
        ret= self.runMultipart("/relationship", "GETOUTBOUNDRELATIONSHIPS", params)
        return ret['response']

    def doRelationship_GetInboundRelationships(self,relationshipRepoURI,toURI):
        '''
        Gets all the relationship links with the specified Rapture resource as the "to" half
        of the link.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipRepoURI'] = self.fixTypes(relationshipRepoURI)
        params['toURI'] = self.fixTypes(toURI)
        ret= self.runMultipart("/relationship", "GETINBOUNDRELATIONSHIPS", params)
        return ret['response']

    def doRelationship_GetLabledRelationships(self,relationshipRepoURI,relationshipLabel):
        '''
        Gets all the relationship links with the specified label.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipRepoURI'] = self.fixTypes(relationshipRepoURI)
        params['relationshipLabel'] = self.fixTypes(relationshipLabel)
        ret= self.runMultipart("/relationship", "GETLABLEDRELATIONSHIPS", params)
        return ret['response']

    def doRelationship_GetChildren(self,prefix):
        '''
        Get children (nodes) in a relationship store. Relationship stores are only one level
        deep, so this API exists only to provide a consistent API as other repository types.
        This method is not useful except when making generic repository browsers.
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        ret= self.runMultipart("/relationship", "GETCHILDREN", params)
        return ret['response']

    def doRelationship_GetAllChildrenMap(self,prefix):
        '''
        Return full pathnames for an entire subtree as a map of path to RFI
        '''
        params = {}
        params['context'] = self.context
        params['prefix'] = self.fixTypes(prefix)
        ret= self.runMultipart("/relationship", "GETALLCHILDRENMAP", params)
        return ret['response']

    def doRelationship_GetRelationshipCenteredOn(self,relationshipNodeURI,options):
        '''
        Gets relationships from a given node.
        '''
        params = {}
        params['context'] = self.context
        params['relationshipNodeURI'] = self.fixTypes(relationshipNodeURI)
        params['options'] = self.fixTypes(options)
        ret= self.runMultipart("/relationship", "GETRELATIONSHIPCENTEREDON", params)
        return ret['response']

    def doEnvironment_GetNetworkInfo(self):
        '''
        Retrieves the unique identifier and name for this Rapture instance.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/environment", "GETNETWORKINFO", params)
        return ret['response']

    def doEnvironment_SetNetworkInfo(self,network):
        '''
        Applies network information matching the passed parameter to the current instance
        of the Rapture network.
        '''
        params = {}
        params['context'] = self.context
        params['network'] = self.fixTypes(network)
        ret= self.runMultipart("/environment", "SETNETWORKINFO", params)
        return ret['response']

    def doEnvironment_GetThisServer(self):
        '''
        Retrieves the unique identifier and name for this Rapture server instance.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/environment", "GETTHISSERVER", params)
        return ret['response']

    def doEnvironment_GetServers(self):
        '''
        Returns a list of the unique identifiers and names for all Rapture servers in the
        network.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/environment", "GETSERVERS", params)
        return ret['response']

    def doEnvironment_SetThisServer(self,info):
        '''
        Sets the passed parameter as information for the current server instance.
        '''
        params = {}
        params['context'] = self.context
        params['info'] = self.fixTypes(info)
        ret= self.runMultipart("/environment", "SETTHISSERVER", params)
        return ret['response']

    def doEnvironment_SetApplianceMode(self,mode):
        '''
        Configures the instance into or out of appliance mode.
        '''
        params = {}
        params['context'] = self.context
        params['mode'] = self.fixTypes(mode)
        ret= self.runMultipart("/environment", "SETAPPLIANCEMODE", params)
        return ret['response']

    def doEnvironment_GetApplianceMode(self):
        '''
        Determines whether the instance is currently in appliance mode.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/environment", "GETAPPLIANCEMODE", params)
        return ret['response']

    def doEnvironment_GetServerStatus(self):
        '''
        Returns the last reported state for each server in the network. This includes a numerical
        status, a human readable message, and a Date object indicating the time that the
        status was last updated.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/environment", "GETSERVERSTATUS", params)
        return ret['response']

    def doEnvironment_GetLicenseInfo(self):
        '''
        Returns the licensee name, license expiration date, and whether the license is a
        developer license.
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/environment", "GETLICENSEINFO", params)
        return ret['response']

    def doQuestion_PutTemplate(self,qTemplateURI,template):
        '''
        Defines or redefines a question template.
        '''
        params = {}
        params['context'] = self.context
        params['qTemplateURI'] = self.fixTypes(qTemplateURI)
        params['template'] = self.fixTypes(template)
        ret= self.runMultipart("/question", "PUTTEMPLATE", params)
        return ret['response']

    def doQuestion_GetTemplate(self,qTemplateURI):
        '''
        Retrieves a question template.
        '''
        params = {}
        params['context'] = self.context
        params['qTemplateURI'] = self.fixTypes(qTemplateURI)
        ret= self.runMultipart("/question", "GETTEMPLATE", params)
        return ret['response']

    def doQuestion_GetQuestion(self,questionURI):
        '''
        Retrieve a question for a URI.
        '''
        params = {}
        params['context'] = self.context
        params['questionURI'] = self.fixTypes(questionURI)
        ret= self.runMultipart("/question", "GETQUESTION", params)
        return ret['response']

    def doQuestion_AskQuestion(self,qTemplateURI,variables,callback):
        '''
        Asks a question using a template. The callback may not contain slashes.
        '''
        params = {}
        params['context'] = self.context
        params['qTemplateURI'] = self.fixTypes(qTemplateURI)
        params['variables'] = self.fixTypes(variables)
        params['callback'] = self.fixTypes(callback)
        ret= self.runMultipart("/question", "ASKQUESTION", params)
        return ret['response']

    def doQuestion_GetQNotifications(self,search):
        '''
        Lists what questions are pending for a given condition.
        '''
        params = {}
        params['context'] = self.context
        params['search'] = self.fixTypes(search)
        ret= self.runMultipart("/question", "GETQNOTIFICATIONS", params)
        return ret['response']

    def doQuestion_GetQNotificationURIs(self,search):
        '''
        Gets the URIs for a questionSearch.
        '''
        params = {}
        params['context'] = self.context
        params['search'] = self.fixTypes(search)
        ret= self.runMultipart("/question", "GETQNOTIFICATIONURIS", params)
        return ret['response']

    def doQuestion_AnswerQuestion(self,questionURI,response,data):
        '''
        Attaches an answer to the given question.
        '''
        params = {}
        params['context'] = self.context
        params['questionURI'] = self.fixTypes(questionURI)
        params['response'] = self.fixTypes(response)
        params['data'] = self.fixTypes(data)
        ret= self.runMultipart("/question", "ANSWERQUESTION", params)
        return ret['response']

    def doStructured_CreateStructuredRepo(self,uri,config):
        '''
        Create a repository for structured data
        '''
        params = {}
        params['context'] = self.context
        params['uri'] = self.fixTypes(uri)
        params['config'] = self.fixTypes(config)
        ret= self.runMultipart("/structured", "CREATESTRUCTUREDREPO", params)
        return ret['response']

    def doStructured_DeleteStructuredRepo(self,uri):
        '''
        Delete a repository for structured data
        '''
        params = {}
        params['context'] = self.context
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/structured", "DELETESTRUCTUREDREPO", params)
        return ret['response']

    def doStructured_StructuredRepoExists(self,uri):
        '''
        check existence
        '''
        params = {}
        params['context'] = self.context
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/structured", "STRUCTUREDREPOEXISTS", params)
        return ret['response']

    def doStructured_GetStructuredRepoConfig(self,uri):
        '''
        get a specific structured repo config given a uri
        '''
        params = {}
        params['context'] = self.context
        params['uri'] = self.fixTypes(uri)
        ret= self.runMultipart("/structured", "GETSTRUCTUREDREPOCONFIG", params)
        return ret['response']

    def doStructured_GetStructuredRepoConfigs(self):
        '''
        get list of all configurations
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/structured", "GETSTRUCTUREDREPOCONFIGS", params)
        return ret['response']

    def doStructured_CreateTableUsingSql(self,schema,rawSql):
        '''
        create a structured table using raw sql
        '''
        params = {}
        params['context'] = self.context
        params['schema'] = self.fixTypes(schema)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "CREATETABLEUSINGSQL", params)
        return ret['response']

    def doStructured_CreateTable(self,tableUri,columns):
        '''
        create a structured table using a column name to SQL column type map
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columns'] = self.fixTypes(columns)
        ret= self.runMultipart("/structured", "CREATETABLE", params)
        return ret['response']

    def doStructured_DropTable(self,tableUri):
        '''
        drop a structured table and all of its data
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        ret= self.runMultipart("/structured", "DROPTABLE", params)
        return ret['response']

    def doStructured_TableExists(self,tableUri):
        '''
        check if table exists
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        ret= self.runMultipart("/structured", "TABLEEXISTS", params)
        return ret['response']

    def doStructured_DescribeTable(self,tableUri):
        '''
        get table description
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        ret= self.runMultipart("/structured", "DESCRIBETABLE", params)
        return ret['response']

    def doStructured_AddTableColumns(self,tableUri,columns):
        '''
        add column(s) to an existing table.  Table must exist beforehand
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columns'] = self.fixTypes(columns)
        ret= self.runMultipart("/structured", "ADDTABLECOLUMNS", params)
        return ret['response']

    def doStructured_DeleteTableColumns(self,tableUri,columnNames):
        '''
        remove column(s) from an existing table.  Table must exist beforehand
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columnNames'] = self.fixTypes(columnNames)
        ret= self.runMultipart("/structured", "DELETETABLECOLUMNS", params)
        return ret['response']

    def doStructured_UpdateTableColumns(self,tableUri,columns):
        '''
        update column(s) in an existing table.  Table must exist beforehand
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columns'] = self.fixTypes(columns)
        ret= self.runMultipart("/structured", "UPDATETABLECOLUMNS", params)
        return ret['response']

    def doStructured_RenameTableColumns(self,tableUri,columnNames):
        '''
        rename column(s) in an existing table.  Table must exist beforehand
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columnNames'] = self.fixTypes(columnNames)
        ret= self.runMultipart("/structured", "RENAMETABLECOLUMNS", params)
        return ret['response']

    def doStructured_CreateIndex(self,tableUri,indexName,columnNames):
        '''
        create an index on a structured table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['indexName'] = self.fixTypes(indexName)
        params['columnNames'] = self.fixTypes(columnNames)
        ret= self.runMultipart("/structured", "CREATEINDEX", params)
        return ret['response']

    def doStructured_DropIndex(self,tableUri,indexName):
        '''
        remove an index that was previously created on a table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['indexName'] = self.fixTypes(indexName)
        ret= self.runMultipart("/structured", "DROPINDEX", params)
        return ret['response']

    def doStructured_SelectJoinedRows(self,tableUris,columnNames,p_from,where,order,ascending,limit):
        '''
        retrieve data from multiple tables
        '''
        params = {}
        params['context'] = self.context
        params['tableUris'] = self.fixTypes(tableUris)
        params['columnNames'] = self.fixTypes(columnNames)
        params['from'] = self.fixTypes(p_from)
        params['where'] = self.fixTypes(where)
        params['order'] = self.fixTypes(order)
        params['ascending'] = self.fixTypes(ascending)
        params['limit'] = self.fixTypes(limit)
        ret= self.runMultipart("/structured", "SELECTJOINEDROWS", params)
        return ret['response']

    def doStructured_SelectUsingSql(self,schema,rawSql):
        '''
        retrieve data with raw sql
        '''
        params = {}
        params['context'] = self.context
        params['schema'] = self.fixTypes(schema)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "SELECTUSINGSQL", params)
        return ret['response']

    def doStructured_SelectRows(self,tableUri,columnNames,where,order,ascending,limit):
        '''
        retrieve data from a single table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columnNames'] = self.fixTypes(columnNames)
        params['where'] = self.fixTypes(where)
        params['order'] = self.fixTypes(order)
        params['ascending'] = self.fixTypes(ascending)
        params['limit'] = self.fixTypes(limit)
        ret= self.runMultipart("/structured", "SELECTROWS", params)
        return ret['response']

    def doStructured_InsertUsingSql(self,schema,rawSql):
        '''
        insert new data with raw sql
        '''
        params = {}
        params['context'] = self.context
        params['schema'] = self.fixTypes(schema)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "INSERTUSINGSQL", params)
        return ret['response']

    def doStructured_InsertRow(self,tableUri,values):
        '''
        insert new data into a single table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['values'] = self.fixTypes(values)
        ret= self.runMultipart("/structured", "INSERTROW", params)
        return ret['response']

    def doStructured_InsertRows(self,tableUri,values):
        '''
        insert one or more rows of data into a single table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['values'] = self.fixTypes(values)
        ret= self.runMultipart("/structured", "INSERTROWS", params)
        return ret['response']

    def doStructured_DeleteUsingSql(self,schema,rawSql):
        '''
        delete data with raw sql
        '''
        params = {}
        params['context'] = self.context
        params['schema'] = self.fixTypes(schema)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "DELETEUSINGSQL", params)
        return ret['response']

    def doStructured_DeleteRows(self,tableUri,where):
        '''
        delete data from a single table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['where'] = self.fixTypes(where)
        ret= self.runMultipart("/structured", "DELETEROWS", params)
        return ret['response']

    def doStructured_UpdateUsingSql(self,schema,rawSql):
        '''
        update existing data with raw sql
        '''
        params = {}
        params['context'] = self.context
        params['schema'] = self.fixTypes(schema)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "UPDATEUSINGSQL", params)
        return ret['response']

    def doStructured_UpdateRows(self,tableUri,values,where):
        '''
        update existing data from a single table
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['values'] = self.fixTypes(values)
        params['where'] = self.fixTypes(where)
        ret= self.runMultipart("/structured", "UPDATEROWS", params)
        return ret['response']

    def doStructured_Begin(self):
        '''
        start a transaction
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/structured", "BEGIN", params)
        return ret['response']

    def doStructured_Commit(self):
        '''
        commit a transaction
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/structured", "COMMIT", params)
        return ret['response']

    def doStructured_Rollback(self):
        '''
        rollback a transaction
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/structured", "ROLLBACK", params)
        return ret['response']

    def doStructured_Abort(self,transactionId):
        '''
        abort a transaction of given id
        '''
        params = {}
        params['context'] = self.context
        params['transactionId'] = self.fixTypes(transactionId)
        ret= self.runMultipart("/structured", "ABORT", params)
        return ret['response']

    def doStructured_GetTransactions(self):
        '''
        get active transactions
        '''
        params = {}
        params['context'] = self.context
        ret= self.runMultipart("/structured", "GETTRANSACTIONS", params)
        return ret['response']

    def doStructured_GetDdl(self,uri,includeTableData):
        '''
        generate the DDL sql that represents an entire schema or an individual table in the
        schema
        '''
        params = {}
        params['context'] = self.context
        params['uri'] = self.fixTypes(uri)
        params['includeTableData'] = self.fixTypes(includeTableData)
        ret= self.runMultipart("/structured", "GETDDL", params)
        return ret['response']

    def doStructured_GetCursorUsingSql(self,schema,rawSql):
        '''
        retrieve a cursor for row-by-row access to data using raw sql
        '''
        params = {}
        params['context'] = self.context
        params['schema'] = self.fixTypes(schema)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "GETCURSORUSINGSQL", params)
        return ret['response']

    def doStructured_GetCursor(self,tableUri,columnNames,where,order,ascending,limit):
        '''
        retrieve a cursor for row-by-row access to data
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['columnNames'] = self.fixTypes(columnNames)
        params['where'] = self.fixTypes(where)
        params['order'] = self.fixTypes(order)
        params['ascending'] = self.fixTypes(ascending)
        params['limit'] = self.fixTypes(limit)
        ret= self.runMultipart("/structured", "GETCURSOR", params)
        return ret['response']

    def doStructured_GetCursorForJoin(self,tableUris,columnNames,p_from,where,order,ascending,limit):
        '''
        retrieve a cursor for data from multiple tables
        '''
        params = {}
        params['context'] = self.context
        params['tableUris'] = self.fixTypes(tableUris)
        params['columnNames'] = self.fixTypes(columnNames)
        params['from'] = self.fixTypes(p_from)
        params['where'] = self.fixTypes(where)
        params['order'] = self.fixTypes(order)
        params['ascending'] = self.fixTypes(ascending)
        params['limit'] = self.fixTypes(limit)
        ret= self.runMultipart("/structured", "GETCURSORFORJOIN", params)
        return ret['response']

    def doStructured_Next(self,tableUri,cursorId,count):
        '''
        given a cursor id, get the next row in the result set
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['cursorId'] = self.fixTypes(cursorId)
        params['count'] = self.fixTypes(count)
        ret= self.runMultipart("/structured", "NEXT", params)
        return ret['response']

    def doStructured_Previous(self,tableUri,cursorId,count):
        '''
        given a cursor id, get the next row in the result set
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['cursorId'] = self.fixTypes(cursorId)
        params['count'] = self.fixTypes(count)
        ret= self.runMultipart("/structured", "PREVIOUS", params)
        return ret['response']

    def doStructured_CloseCursor(self,tableUri,cursorId):
        '''
        close a cursor once done with it
        '''
        params = {}
        params['context'] = self.context
        params['tableUri'] = self.fixTypes(tableUri)
        params['cursorId'] = self.fixTypes(cursorId)
        ret= self.runMultipart("/structured", "CLOSECURSOR", params)
        return ret['response']

    def doStructured_CreateProcedureCallUsingSql(self,procUri,rawSql):
        '''
        Create a stored procedure with raw SQL
        '''
        params = {}
        params['context'] = self.context
        params['procUri'] = self.fixTypes(procUri)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "CREATEPROCEDURECALLUSINGSQL", params)
        return ret['response']

    def doStructured_CallProcedure(self,procUri,params):
        '''
        Call a stored procedure a value
        '''
        params = {}
        params['context'] = self.context
        params['procUri'] = self.fixTypes(procUri)
        params['params'] = self.fixTypes(params)
        ret= self.runMultipart("/structured", "CALLPROCEDURE", params)
        return ret['response']

    def doStructured_DropProcedureUsingSql(self,procUri,rawSql):
        '''
        Delete a stored procedure with raw SQL
        '''
        params = {}
        params['context'] = self.context
        params['procUri'] = self.fixTypes(procUri)
        params['rawSql'] = self.fixTypes(rawSql)
        ret= self.runMultipart("/structured", "DROPPROCEDUREUSINGSQL", params)
        return ret['response']

