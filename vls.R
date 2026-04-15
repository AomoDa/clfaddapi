library(rvest)
library(RCurl)
library(stringr)
library(httr)


# 从节点名称中提取地区
get_region <- function(name) {
	if(grepl("香港|HK|HKG", name)) return("香港")
	if(grepl("台湾|TW|台灣", name)) return("台湾")
	if(grepl("日本|JP", name)) return("日本")
	if(grepl("韩国|KR|韓國", name)) return("韩国")
	if(grepl("新加坡|SG", name)) return("新加坡")
	if(grepl("美国|US", name)) return("美国")
	if(grepl("荷兰|NL", name)) return("荷兰")
	if(grepl("印度|IN", name)) return("印度")
	if(grepl("英国|UK|GB", name)) return("英国")
	if(grepl("德国|DE", name)) return("德国")
	if(grepl("法国|FR", name)) return("法国")
	if(grepl("澳洲|AU", name)) return("澳洲")
	return("其他")
}

# 提取 vless 节点信息并保留原始节点名称
# 每个地区最多提取 max_per_region 个节点
getVlessInfo <- function(txt, max_per_region = 3){
	rlt = c()
	dom = c()
	region_count = list()  # 记录每个地区已提取的数量

	# 将所有 vless:// 开头的节点分离出来
	# 节点之间可能没有换行符，需要用 vless:// 来分割
	txt <- gsub("vless://", "\nvless://", txt)
	txt <- gsub("vmess://", "\nvmess://", txt)
	node_list <- str_split(txt, "\n")[[1]]

	for (i in node_list) {
		if(is.na(i) || i == "") next()
		if(!grepl("^(vless|vmess)://", i)) next()

		# 解码 URL
		decoded <- URLdecode(i)

		# 提取节点名称 (#后面的内容)
		name_match <- str_match(decoded, "#(.+)$")
		if(is.na(name_match[1,1])) next()
		name <- name_match[,2]

		# 提取 server 和 port (在@之后，?或#之前的部分)
		server_port_match <- str_match(decoded, "@([^@?#]+)")
		if(is.na(server_port_match[1,1])) next()
		server_port <- server_port_match[,2]

		# 分离 server 和 port
		sp_parts <- str_split(server_port, ":")[[1]]
		if(length(sp_parts) < 2) next()
		server <- sp_parts[1]
		port <- sp_parts[2]

		# 去重检查
		if(server %in% dom) next()

		# 获取地区
		region <- get_region(name)

		# 检查该地区是否已达到上限
		current_count <- ifelse(is.null(region_count[[region]]), 0, region_count[[region]])
		if(current_count >= max_per_region) next()

		# 记录该地区数量 +1
		region_count[[region]] <- current_count + 1

		rlt <- append(rlt, sprintf("%s:%s#%s", server, port, name))
		dom <- append(dom, server)
	}

	message(sprintf("提取情况：%s",
		paste(names(region_count), unlist(region_count), sep="=", collapse=", ")))
	return(rlt)
}

# 从订阅链接获取数据
getApiData <- function(sub_url = "https://sub.995677.xyz/sub"){

	# 写入预设的备用节点
	write.table(
		x = data.frame(x = c(
			"cf.090227.xyz:443#CF",
			"saas.sin.fan:443#SAAS",
			"store.ubi.com:443#UBI",
			"cf.danfeng.eu.org:443#DF",
			"cu.877774.xyz:443#CFZU"
		)),
		file = "myips.csv",
		col.names = FALSE,
		row.names = FALSE,
		quote = FALSE
	)

	# 获取订阅内容并解析
	tryCatch({
		sub_content <- GET(sub_url)
		nodes_raw <- rawToChar(sub_content$content)

		# Base64 解码
		nodes_decoded <- base64Decode(nodes_raw)

		# 提取符合条件的节点
		valid_nodes <- getVlessInfo(nodes_decoded)

		if(length(valid_nodes) > 0){
			write.table(
				x = data.frame(x = valid_nodes[1:min(50, length(valid_nodes))]),
				file = "myips.csv",
				col.names = FALSE,
				row.names = FALSE,
				quote = FALSE,
				append = TRUE
			)
			message(sprintf("成功提取 %d 个节点", length(valid_nodes)))
		} else {
			message("未找到符合条件的节点")
		}
	}, error = function(e){
		message(sprintf("获取订阅失败：%s", e$message))
	})
}

# 运行
getApiData()
