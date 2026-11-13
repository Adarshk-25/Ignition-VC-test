def doGet(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# Resource       : MESIntegration/api/health
	#
	# Description:
	# Lightweight health-check endpoint for monitoring the Ignition Gateway,
	# WebDev module, project execution and optional database connectivity.
	#
	# HTTP Method    : GET
	# Version        : 1.0
	###############################################################################
	
	
	
	    response = {
	        "status": "UP",
	        "service": "Ignition SCADA WebDev",
	        "project": "samplequickstart",
	        "gateway": "Ignition-ag-win-ig-dev",
	        "webdev": "UP",
	        "database": "NOT_CHECKED",
	        "timestamp": system.date.format(
	            system.date.now(),
	            "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"
	        )
	    }
	
	    httpStatus = 200
	
	    try:
	        # Optional database check.
	        # Replace with your actual Ignition database connection name.
	        dbConnection = "Dev_MSSQL_Server"
	
	        result = system.db.runScalarQuery(
	            "SELECT 1",
	            dbConnection
	        )
	
	        if int(result) == 1:
	            response["database"] = "UP"
	        else:
	            response["database"] = "DOWN"
	            response["status"] = "DEGRADED"
	            httpStatus = 503
	
	    except Exception as ex:
	        response["database"] = "DOWN"
	        response["status"] = "DEGRADED"
	        response["error"] = str(ex)
	        httpStatus = 503
	
	    return {
	        "json": response,
	        "responseCode": httpStatus
	    }