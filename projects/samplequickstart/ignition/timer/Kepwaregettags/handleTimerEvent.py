def handleTimerEvent():
	logger = system.util.getLogger("KepwareTagStore")
	
	
	# =========================================================
	# GET TAGS
	# =========================================================
	
	def getAllTagsFromFolders(folderPaths):
	
	    allTags = []
	
	    try:
	
	        for folderPath in folderPaths:
	
	            browseResults = system.tag.browse(
	                folderPath
	            ).getResults()
	
	            for tag in browseResults:
	
	                tagType = str(tag['tagType'])
	
	                if tagType == "AtomicTag":
	
	                    allTags.append(
	                        str(tag['fullPath'])
	                    )
	
	                elif tagType == "Folder":
	
	                    subTags = getAllTagsFromFolders([
	                        str(tag['fullPath'])
	                    ])
	
	                    allTags.extend(subTags)
	
	    except Exception as e:
	
	        logger.error(
	            "Browse Error : %s" % str(e)
	        )
	
	    return allTags
	
	
	# =========================================================
	# STORE TAGS
	# =========================================================
	
	def storeTags():
	
	    logger.info(
	        "Timer fired at %s"
	        % system.date.now()
	    )
	
	    try:
	
	        folders = [
            "[default]DataSource/Agratas/IN11/MES",
            "[default]DataSource/Agratas/IN11/E101/MES",
            "[default]DataSource/Agratas/IN11/E101/PRO/ACAL101/MES",
            "[default]DataSource/Agratas/IN11/E101/PRO/ACOT101/MES",
            "[default]DataSource/Agratas/IN11/E101/PRO/AMIX101/MES",
            "[default]DataSource/Agratas/IN11/E101/PRO/MES",
            ]
	
	        # -------------------------------------------------
	        # GET TAGS
	        # -------------------------------------------------
	
	        tags = getAllTagsFromFolders(folders)
	
	        logger.info(
	            "Tags Found : %d"
	            % len(tags)
	        )
	
	        if len(tags) == 0:
	
	            logger.warn("No tags found")
	
	            return
	
	        # -------------------------------------------------
	        # READ VALUES
	        # -------------------------------------------------
	
	        values = system.tag.readBlocking(tags)
	
	        logger.info("Tag read completed")
	
	        # -------------------------------------------------
	        # INSERT
	        # -------------------------------------------------
	
	        query = """
	
	            INSERT INTO MachineTags
	            (
	                machineId,
	                tagName,
	                tagValue
	            )
	            VALUES
	            (
	                ?,
	                ?,
	                ?
	            )
	
	        """
	
	        machineId = "M" + system.date.format(
	            system.date.now(),
	            "yyyyMMdd"
	        )
	
	        insertedCount = 0
	
	        for i, qv in enumerate(values):
	
	            try:
	
	                if qv.quality.isGood():
	
	                    row = [
	
	                        machineId,
	                        str(tags[i]),
	                        str(qv.value)
	
	                    ]
	
	                    system.db.runPrepUpdate(
	
	                        query,
	                        row,
	                        "Dev_MSSQL_Server"
	
	                    )
	
	                    insertedCount += 1
	
	            except Exception as rowEx:
	
	                logger.error(
	                    "Insert Error : %s"
	                    % str(rowEx)
	                )
	
	        logger.info(
	            "SUCCESS : Inserted %d rows"
	            % insertedCount
	        )
	
	    except Exception as e:
	
	        logger.error(
	            "StoreTags Error : %s"
	            % str(e)
	        )
	
	    logger.info(
	        "Timer execution completed"
	    )
	
	
	# =========================================================
	# EXECUTE
	# =========================================================
	
	storeTags()