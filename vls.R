library(rvest)
library(RCurl)
library(stringr)

isselect = function(tag){
	if(is.na(tag)) return(FALSE)
	vls = c("CF","HKG","HK","hkg","hk","TW","tw")
	str_cnt = sum(str_count(tag,vls))
	if(str_cnt>0) return(TRUE)
	return(FALSE)	
}	

getVlessInfo <- function(txt_list,vname){

	rlt = data.frame();ind = 1;dom=c()
	for (i in txt_list[-1]) {

		info = str_extract(URLdecode(i),".+://[^@]+@([^:]+):(\\d+).+#(.+)",group=c(1,2,3))
		if(isselect(info[3])){
			if(any(dom==info[1])) next()
			tmp = data.frame(ips =sprintf("%s:%s#%s%s",info[1],info[2],vname,ind)) 
			rlt = rbind(rlt,tmp)
			ind = ind + 1
			dom = append(dom,info[1]) 
		}
	}
	return(rlt)
}

getApiData <- function(){

	write.table(x=data.frame(x=c("cf.090227.xyz:443#CF","cdns.doon.eu.org:443#TE1","mfa.gov.ua:443#MFA","www.shopify.com:443#SHOP","store.ubi.com:443#STORE","staticdelivery.nexusmods.com:443#NEX")),file = "myips.csv",col.names = FALSE,row.names = FALSE,quote=FALSE)	
	readLines("xurl2") %>%	
		read_html() %>% 
		html_text2() %>% 
		base64Decode() %>%
		str_split("\n") %>%
		unlist() %>%
		getVlessInfo("TC") %>%
		head(10) %>%
		write.table(file = "myips.csv",col.names = FALSE,row.names = FALSE,quote=FALSE,append=TRUE)
}
# run
getApiData()
