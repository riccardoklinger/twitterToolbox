import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "TweetCollector"
        self.alias = "Tweet Collector"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tweet Collector"
        self.description = "Collect tweets in real time or with a historic view"
        self.canRunInBackground = False

    def getParameterInfo(self):
        '''Define parameter definitions'''
        # First parameter
        hashtags = arcpy.Parameter(
            displayName='Search String',
            name='hashtags',
            datatype='GPString',
            parameterType='Optional',
            direction='Input')
        out_feature = arcpy.Parameter(
            displayName='Output Point Feature Class Name',
            name='out_feature',
            datatype='GPString',
            parameterType='Required',
            direction='Output')
        Extent = arcpy.Parameter(
            displayName='Extent',
            name='Lat',
            datatype='GPExtent',
            parameterType='Optional',
            direction='Input')
        locationType = arcpy.Parameter(
            displayName='Location Type',
            name='locType',
            datatype='GPString',
            parameterType='Required',
            direction='Input')
        locationType.filter.type = 'ValueList'
        locationType.filter.list = ['user location', 'place location']
        locationType.value = locationType.filter.list[0]
        collType= arcpy.Parameter(
            displayName='Collection Type',
            name='colType',
            datatype='GPString',
            parameterType='Required',
            direction='Input')
        collType.filter.type = 'ValueList'
        collType.filter.list = ['historic', 'real time']
        collType.value = collType.filter.list[0]
        numberOfTweets= arcpy.Parameter(
            displayName='Number of Tweets',
            name='numberOfTweets',
            datatype='GPLong',
            parameterType='required',
            direction='Input')
        numberOfTweets.value = 100
        timeForTweets= arcpy.Parameter(
            displayName='max. duration [s] of realtime stream',
            name='Duration',
            datatype='GPLong',
            parameterType='required',
            direction='Input')
        timeForTweets.value = 60
        params = [hashtags, out_feature, Extent, locationType, collType, numberOfTweets, timeForTweets]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""

        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""
        if parameters[0].valueAsText and parameters[4].value=="real time":
            if parameters[2].value:
                parameters[0].value=""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return
    def execute(self, parameters, messages):
        """The source code of the tool."""
        def createFC(name):
            import time
            sr = arcpy.SpatialReference(4326)
            arcpy.CreateFeatureclass_management(arcpy.env.workspace, name, 'POINT',"", "", "", sr)
            arcpy.AddField_management(name, "username", "TEXT", "", "", 255, "username", "NON_NULLABLE", "REQUIRED")
            arcpy.AddField_management(name, "tweet", "TEXT", "", "", 255, "tweet", "NON_NULLABLE", "REQUIRED")
            arcpy.AddField_management(name, "time", "DATE", "", "", "", "time", "NON_NULLABLE", "REQUIRED")
            arcpy.AddField_management(name, "place", "TEXT", "", "", 255, "place_name", "NULLABLE", "NON_REQUIRED")
            arcpy.AddField_management(name, "id", "TEXT", "", "", 255, "id", "NON_NULLABLE", "REQUIRED")
            return
        def insertRecord(tuple, name):
            cursor = arcpy.da.InsertCursor(arcpy.env.workspace + os.sep + name,['username', 'tweet', 'time', 'place', 'id', 'SHAPE@XY'])
            #arcpy.AddMessage(name)
            try: 
                cursor.insertRow(tuple)
            except Exception as e:
                arcpy.AddError(e)
            del cursor
            return
        def accessTweet(inTweet, locationType, resultingNumbers, name):
        #tweets have three types of location: user, place, account. we are just interested in the first two.
            from datetime import datetime
            numberIncreaser = 0
            if locationType == "place location":              
                if inTweet.place != None:
                #places are displayed with bounding boxes:
                    tweetTuple = (inTweet.user.name, inTweet.text, inTweet.created_at.strftime('%Y-%m-%d %H:%M'), inTweet.place.full_name, str(inTweet.id),((inTweet.place.bounding_box.coordinates[0][2][0] + inTweet.place.bounding_box.coordinates[0][0][0]) / 2, (inTweet.place.bounding_box.coordinates[0][2][1] + inTweet.place.bounding_box.coordinates[0][0][1]) / 2))
                    insertRecord(tweetTuple, name)
                    numberIncreaser = 1
            if locationType == "user location":         
                if inTweet.coordinates != None:
                    #places are displayed with bounding boxes:
                    tweetTuple = (inTweet.user.name, inTweet.text, inTweet.created_at.strftime('%Y-%m-%d %H:%M'), "device coordinates", str(inTweet.id),(inTweet.coordinates['coordinates'][0], inTweet.coordinates['coordinates'][1]))
                    insertRecord(tweetTuple, name)
                    numberIncreaser = 1
            return numberIncreaser
        try:
            import tweepy, json
            arcpy.AddMessage("Tweepy was found!")
        except:
            arcpy.AddError("Check dependencies: tweepy, json")
        #setting the authentication:
        
        consumerKey = "XXX" #set your key here
        consumerSecret = "XXX" #set your key here
        accessToken = "XXX" #set your key here
        accessTokenSecret = "XXX" #set your key here
        key = tweepy.OAuthHandler(consumerKey, consumerSecret)
        key.set_access_token(accessToken, accessTokenSecret)
        api = tweepy.API(key, wait_on_rate_limit=True,wait_on_rate_limit_notify=True)
        #create a featureClass:
        import time
        name = parameters[1].value + str(time.time()).split('.')[0]
        createFC(name)

        #struggling with the extent:
        if parameters[2].value:
            rectangle = [[parameters[2].value.XMin,parameters[2].value.YMin],[parameters[2].value.XMin,parameters[2].value.YMax],[parameters[2].value.XMax,parameters[2].value.YMax],[parameters[2].value.XMax,parameters[2].value.YMin]]
            extent=arcpy.Polygon(arcpy.Array([arcpy.Point(*coords) for coords in rectangle]))
            arcpy.AddMessage("search in a region!")
            LL = arcpy.PointGeometry(arcpy.Point(parameters[2].value.XMin, parameters[2].value.YMin),arcpy.SpatialReference(4326))
            UR = arcpy.PointGeometry(arcpy.Point(parameters[2].value.XMax, parameters[2].value.YMax),arcpy.SpatialReference(4326))
            radius=UR.angleAndDistanceTo(LL, method="GEODESIC")[1]/2000 # describes a circle from LL to UR with radius half the size of inputs
            geo=str(extent.centroid.Y) + "," + str(extent.centroid.X) + "," + str(radius) + "km"
        else :
            arcpy.AddMessage("worlwide search!")  
            geo=""     
        if parameters[4].value == "historic":
            arcpy.AddMessage("start: collecting historic tweets")
            tweetsPerQry = 100 # that is the maximum possible
            tweetCount = 0
            max_id = 0
            while tweetCount <= parameters[5].value:
                try:
                    tweetInResponse = 0
                    if (max_id <= 0):
                        new_tweets = api.search(q=str(parameters[0].value), count=tweetsPerQry, geocode=geo)
                    else:
                        new_tweets = api.search(q=str(parameters[0].value), count=tweetsPerQry, geocode=geo, max_id=str(max_id - 1))
                    max_id = new_tweets[-1].id
                    for tweet in new_tweets:
                        tweetInResponse += accessTweet(tweet, parameters[3].value, tweetCount, name)
                except: 
                    arcpy.AddError("no other tweets found!")
                    tweetCount += 1
                    break
                tweetCount += tweetInResponse
                arcpy.AddMessage(str(tweetCount) + " tweets found...")
        if parameters[4].value == "real time":

            arcpy.AddMessage("start: collecting real time tweets")
            start_time = time.time() #start time
            class stream2lib(tweepy.StreamListener):
                def __init__(self, api=None):
                    #api = tweepy.API(key)
                    self.api = api
                    self.n = 0
                def on_status(self, status):
                    #self.output[status.id] = {
                    #'tweet':status.text.encode('utf8'),
                    #'user':status.user.name,
                    #'geo':status.geo,
                    #'place':status.place,
                    #'localization':status.user.location,
                    #'time_zone':status.user.time_zone,
                    #'time':status.timestamp_ms}
                    #arcpy.AddMessage(status)
                    if status.geo != None and parameters[3].value == 'user location':
                        self.n = self.n+1
                        arcpy.AddMessage(str(self.n) + " tweets received...")
                        arcpy.AddMessage(str(time.time() - start_time) + "s from " + str(parameters[6].value) + "s")
                        accessTweet(status, parameters[3].value, self.n, name)
                    if status.place != None and parameters[3].value == 'place location':
                        self.n = self.n+1
                        arcpy.AddMessage(str(self.n) + " tweets received...")
                        arcpy.AddMessage(str(time.time() - start_time) + "s from " + str(parameters[6].value) + "s")
                        #arcpy.AddMessage(status)
                        accessTweet(status, parameters[3].value, self.n, name)
                    if self.n >= parameters[5].value:
                        arcpy.AddMessage("Desired number of tweets collected!")
                        return False
                    if (time.time() - start_time) >= parameters[6].value:
                        arcpy.AddMessage("Time limit of " + str(parameters[6].value) + "s reached!" )
                        return False
                    if self.n < parameters[5].value:    
                        return True
            stream = tweepy.streaming.Stream(key, stream2lib())
            if parameters[2].value:
                stream.filter(locations=[parameters[2].value.XMin,parameters[2].value.YMin,parameters[2].value.XMax,parameters[2].value.YMax])
            else:
                stream.filter(track=[parameters[0].value])               
        return
