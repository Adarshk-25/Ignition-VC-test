def doPost(request, session):
	###############################################################################
	# Project        : AGRATAS SCADA - MES Integration
	# File Name      : doPost.py
	# Module         : Recipe Download WebDev Endpoint
	#
	# Description:
	# Thin WebDev entry point that routes RecipeDownload REST requests into the
	# common SCADA interface router.
	#
	# Author         : Hari
	# Version        : 1.0
	# Date           : 07-Jul-2026
	#
	# Change History
	# -----------------------------------------------------------------------------
	# Sl No | Version | Date        | Author | Fix/Change
	# -----------------------------------------------------------------------------
	# 1     | 1.0     | 07-Jul-2026 | Hari   | Initial documented version
	# -----------------------------------------------------------------------------
	###############################################################################
	
	from scada_interface import router
	
	
	# -----------------------------------------------------------------------------
	# Function    : doPost
	# Description : Handles doPost logic for this module.
	# -----------------------------------------------------------------------------
	# Keep endpoint scripts thin; shared router handles auth, audit and errors.
	return router.handle_rest_request(
	interface_name="RecipeDownload",
	direction="M2S_TO_S2E",
	request=request
	)