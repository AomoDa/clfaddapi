library(rvest)
library(RCurl)
library(stringr)

isselect = function(tag){
	if(is.na(tag)) return(FALSE)
	vls = c("HKG","HK","hkg","hk","TW","tw","KR")
	str_cnt = sum(str_count(tag,vls))
	if(str_cnt>0) return(TRUE)
	return(FALSE)	
}	

getVlessInfo <- function(txt_list){

	rlt = data.frame();ind = 1;dom=c()
	for (i in txt_list) {

		info = str_extract(URLdecode(i),".+://[^@]+@([^:]+):(\\d+).+#(.+)",group=c(1,2,3))
		if(isselect(info[3])){
			if(any(dom==info[1])) next()
			tmp = data.frame(ips =sprintf("%s:%s#HK%s",info[1],info[2],ind)) 
			rlt = rbind(rlt,tmp)
			ind = ind + 1
			dom = append(dom,info[1]) 
		}
	}
	return(rlt)

}


getApiData <- function(xurl){

	read_html(xurl) %>% 
		html_text2() %>% 
		base64Decode() %>%
		str_split("\n") %>%
		unlist() %>%
		getVlessInfo() %>%
		head(10) %>%
		write.table(file = "myips.csv",col.names = FALSE,row.names = FALSE,quote=FALSE)

}


# run
#getApiData("https://alvless.filegear-sg.me/sub?host=host&uuid=uuid")
#getApiData("https://altrojan.comorg.us.kg/sub?host=host&pw=uuid&path=xpath")
getApiData("https://trojan.cmliussss.net/sub?host=host&pw=uuid&path=xpath")

