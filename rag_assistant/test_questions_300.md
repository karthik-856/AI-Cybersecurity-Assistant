# Zuka 300-Question Test Set


## In Domain

1. **Q001** — What is the primary mission of the ZUKA SOC Platform?

2. **Q002** — Why do smart devices require dedicated SOC operations instead of traditional antivirus or EDR agents?

3. **Q003** — What default credentials do smart devices frequently ship with?

4. **Q004** — What is the consequence of unpatched firmware in smart devices?

5. **Q005** — How are compromised IoT devices weaponized by attackers?

6. **Q006** — What role does Zuka the assistant act as in the SOC?

7. **Q007** — What is Zuka's policy regarding hallucinations and database queries?

8. **Q008** — How does Zuka enforce its strict defensive boundary?

9. **Q009** — What ports or unencrypted management daemons are common insecure defaults on smart hardware?

10. **Q010** — Can Zuka generate exploit payloads if requested by an analyst?

11. **Q011** — What frontend technologies and framework are used in the ZUKA platform?

12. **Q012** — What icon library is used in the frontend UI?

13. **Q013** — Which Python version and web framework power the backend API?

14. **Q014** — What ASGI server runs the FastAPI backend?

15. **Q015** — What database, ORM, and migration tools are used for persistence?

16. **Q016** — What machine learning algorithm powers network threat classification in ZUKA?

17. **Q017** — Across how many traffic categories is the ML model trained?

18. **Q018** — How many network flows were used to train the XGBoost model?

19. **Q019** — What tool provides explainable AI in the ZUKA platform?

20. **Q020** — What is the operational responsibility of TreeSHAP in the platform?

21. **Q021** — What local AI assistant engine and regex engine are utilized?

22. **Q022** — What authorization mechanism is used by the backend API?

23. **Q023** — What operations are permitted for the ADMIN role?

24. **Q024** — What is the critical safety safeguard preventing admin lockout?

25. **Q025** — What modules can a SOC_ANALYST access in ZUKA?

26. **Q026** — What operational constraints apply to the SOC_ANALYST role?

27. **Q027** — What permissions are granted to the VIEWER role?

28. **Q028** — What actions is the VIEWER role prohibited from performing?

29. **Q029** — What is the default account status for newly registered users?

30. **Q030** — How can an administrator authorize a newly registered analyst?

31. **Q031** — What does the Dashboard module (/dashboard) display?

32. **Q032** — What protocols are broken down on the Dashboard?

33. **Q033** — What telemetry does the Network Monitor (/network-monitor) visualize?

34. **Q034** — What is the operational function of the Alert Center (/alerts)?

35. **Q035** — What must analysts click in the Alert Center before an investigation can be unlocked?

36. **Q036** — What is the full lifecycle case progression in Incident Management (/incidents)?

37. **Q037** — What priority ratings are supported in Incident Management?

38. **Q038** — What escalation tiers exist in Incident Management?

39. **Q039** — What does the Defense Department (/defense) filter exclusively for?

40. **Q040** — List the tactical containment countermeasures supported in the Defense Department.

41. **Q041** — Where are applied defense directives logged and appended?

42. **Q042** — What prefixes do digital forensic case dossiers use in the Investigation Department?

43. **Q043** — What manual action by the analyst unlocks incident resolution in the Investigation Department?

44. **Q044** — What report types can be generated in the Reports & PDF Export module (/reports)?

45. **Q045** — How does the PDF export module ensure clean white paper printing?

46. **Q046** — What is displayed in the Database Center (/databases)?

47. **Q047** — What security controls are managed under Settings & Security (/settings)?

48. **Q048** — What validation multiclass accuracy does the XGBoost model achieve?

49. **Q049** — What is the validation F1 score on DDoS traffic?

50. **Q050** — What is the validation F1 score on DoS traffic?

51. **Q051** — What is the validation F1 score on Benign traffic?

52. **Q052** — What severity is typically assigned to BENIGN traffic?

53. **Q053** — What network behavior characterizes the DOS attack class?

54. **Q054** — What network behavior characterizes DDOS?

55. **Q055** — What typical severity is assigned to PORT_SCAN attacks?

56. **Q056** — What ports are typically targeted during BRUTE_FORCE attacks?

57. **Q057** — What network signature characterizes BOTNET activity?

58. **Q058** — What is the typical severity of BACKDOOR and BOTNET classes?

59. **Q059** — What behavior defines FUZZING attacks?

60. **Q060** — What defines INFILTRATION attacks?

61. **Q061** — What chip architectures are targeted by the MALWARE attack class?

62. **Q062** — List at least 5 of the 14 network flow features evaluated by the model.

63. **Q063** — How does TreeSHAP explain model inference to analysts?

64. **Q064** — How does TreeSHAP help eliminate false alarms on video streaming?

65. **Q065** — What is the mandatory rule when acknowledging an alert under SOP-01?

66. **Q066** — What assistant command can be used to acknowledge an alert in SOP-01?

67. **Q067** — What prerequisite must be verified before starting an investigation in SOP-02?

68. **Q068** — What assistant command initiates an investigation under SOP-02?

69. **Q069** — What status does an incident transition to when investigation starts in SOP-02?

70. **Q070** — What telemetry is reviewed in SOP-03 inside Defense Department?

71. **Q071** — What button applies the containment strategy in SOP-03?

72. **Q072** — Who authors the final conclusion in SOP-04?

73. **Q073** — What status does the investigation transition to in SOP-04 after completing?

74. **Q074** — In SOP-05, where does the incident resolution summary adopt its content from?

75. **Q075** — What timestamp is recorded when an incident is resolved in SOP-05?

76. **Q076** — What assistant command can close an incident in SOP-06?

77. **Q077** — What happens to the incident once status updates to CLOSED in SOP-06?

78. **Q078** — How are reports printed according to SOP-07?

79. **Q079** — Explain Zuka's Dual-Engine Architecture.

80. **Q080** — How long is the confirmation token valid for destructive actions like user deletion?

81. **Q081** — What does the command 'show alert <id>' do?

82. **Q082** — How many recent threat detections are displayed by 'list alerts'?

83. **Q083** — Which command filters alerts where severity is CRITICAL?

84. **Q084** — Which command marks an alert as FALSE_POSITIVE?

85. **Q085** — Which command promotes an alert into a formal security incident?

86. **Q086** — What does the command 'show incident <id>' display?

87. **Q087** — Which command lists all active security cases in an ActionTable?

88. **Q088** — Which command filters incidents currently in OPEN status?

89. **Q089** — What is required when running the command 'resolve incident <id>'?

90. **Q090** — Which admin command authorizes a pending analyst account?

91. **Q091** — Which command immediately suspends a user's login access?

92. **Q092** — What does 'system status' check?

93. **Q093** — What does 'dashboard stats' return?

94. **Q094** — What command displays categorized interactive command cards?

95. **Q095** — Does ZUKA send our telemetry or packet data to external cloud APIs?

96. **Q096** — Why can newly registered users not log in immediately according to FAQ Q4?

97. **Q097** — What is the confidence threshold for a CRITICAL alert?

98. **Q098** — What is the confidence threshold for a HIGH severity alert?

99. **Q099** — What is the confidence threshold for a MEDIUM severity alert?

100. **Q100** — What is the confidence threshold for a LOW severity alert?

101. **Q101** — What does Explainable AI (TreeSHAP) show analysts in an alert?

102. **Q102** — How do analysts distinguish legitimate high-definition video streaming from a DoS flood?

103. **Q103** — Why is the 'Start Investigation' button locked on an incident according to FAQ Q8?

104. **Q104** — What occurs when an investigation is started according to FAQ Q9?

105. **Q105** — What is required before an incident can be marked RESOLVED in FAQ Q10?

106. **Q106** — How do Escalation Levels work in ZUKA according to FAQ Q11?

107. **Q107** — How are user passwords protected in ZUKA?

108. **Q108** — How do session revocations and 2FA work according to FAQ Q13?

109. **Q109** — What happens if an administrator attempts to delete their own account according to FAQ Q14?

110. **Q110** — Why does user deletion require a confirmation token in FAQ Q15?

111. **Q111** — What happens if Ollama is not running on localhost:11434 according to FAQ Q16?

112. **Q112** — How do I verify live system and database health according to FAQ Q17?

113. **Q113** — What is Directive 1 of the Core Assistant Guardrails?

114. **Q114** — What is Directive 2 regarding SOP enforcement?

115. **Q115** — What is Directive 3 regarding safety confirmation?

116. **Q116** — What is Directive 4 regarding defensive boundaries?

117. **Q117** — What tone and format is mandated by Directive 5 (Concise Professionalism)?

118. **Q118** — What kinds of attacks does the ZUKA SOC Platform specifically detect?

119. **Q119** — Why can't microcontrollers run traditional antivirus agents?

120. **Q120** — What protocol on port 23 often exposes smart devices?

121. **Q121** — What type of botnet architecture is mentioned in volumetric weaponization?

122. **Q122** — Does Zuka ever guess operational metrics without a database query?

123. **Q123** — Can Zuka craft malicious network packets for security testing?

124. **Q124** — What tier operations does the Zuka assistant support?

125. **Q125** — What language is the backend API written in?

126. **Q126** — What library handles database migrations?

127. **Q127** — What database is used for storing audit logs and incident ledgers?

128. **Q128** — What is the name of the multiclass decision tree model?

129. **Q129** — How is feature attribution computed for each packet flow?

130. **Q130** — What local LLM engine is integrated into Zuka?

131. **Q131** — How fast does the deterministic regex engine process incoming queries?

132. **Q132** — Can an admin deactivate their own account?

133. **Q133** — Can a SOC_ANALYST modify database schema definitions?

134. **Q134** — Can a VIEWER export PDF reports from the platform?

135. **Q135** — What happens to login credentials immediately after registration?

136. **Q136** — What panel does an administrator use to authorize users?

137. **Q137** — Where can an operator inspect 24h attack distributions?

138. **Q138** — Which module shows port scans and packet burst frequencies?

139. **Q139** — What drawer in Alert Center shows root-cause feature attribution?

140. **Q140** — What happens in Incident Management after an alert is acknowledged?

141. **Q141** — What countermeasure isolates a compromised device into a segregated network?

142. **Q142** — What countermeasure blocks traffic from an adversary's IP address?

143. **Q143** — What countermeasure locks IoT device firmware?

144. **Q144** — What is the prefix used for investigation dossiers?

145. **Q145** — Where is the Analyst Action Ledger located?

146. **Q146** — Where can operators configure TOTP two-factor authentication?

147. **Q147** — What weighting strategy was used during XGBoost model training?

148. **Q148** — What is the attack class for Telnet dictionary attacks?

149. **Q149** — What is the attack class for Mirai-style recruitment?

150. **Q150** — What is the attack class for unauthorized reverse listeners?

151. **Q151** — What is the attack class for active host discovery across subnets?

152. **Q152** — What is the attack class for malformed high-entropy payloads?

153. **Q153** — What is the attack class for lateral movement deeper into internal LAN?

154. **Q154** — What is the attack class for binary payload distribution on ARM/MIPS?

155. **Q155** — What is the typical severity of RECONNAISSANCE traffic?

156. **Q156** — What is the typical severity of EXPLOIT attacks?

157. **Q157** — What feature represents the duration of a network flow?

158. **Q158** — What feature represents destination bytes transferred?

159. **Q159** — What feature represents mean source packet size?

160. **Q160** — What feature represents source inter-arrival time mean?

161. **Q161** — What is the first step in SOP-01?

162. **Q162** — What drawer opens when clicking an alert row in SOP-01?

163. **Q163** — What does SOP-02 require before an incident can be investigated?

164. **Q164** — What does the system auto-provision upon starting an investigation in SOP-02?

165. **Q165** — What module exclusively displays open investigations in SOP-03?

166. **Q166** — What ledger records defense containment events?

167. **Q167** — What must an analyst write in SOP-04 before completing an investigation?

168. **Q168** — What unlocks incident resolution in SOP-05?

169. **Q169** — What timestamp is stamped when an incident is marked RESOLVED?

170. **Q170** — What review is conducted in SOP-06 before closing an incident?

171. **Q171** — What happens if a query matches a deterministic regex pattern?

172. **Q172** — What happens if no regex pattern matches an incoming query?

173. **Q173** — What confirmation window is provided for user deletion?

174. **Q174** — Which command displays the 8 most recent threat detections?

175. **Q175** — Which command marks an alert as RESOLVED?

176. **Q176** — Which command lists all active security cases?

177. **Q177** — Which command transitions an incident to INVESTIGATING and assigns an analyst?

178. **Q178** — Which command lists all registered user accounts?

179. **Q179** — Which command suspends user login access immediately?

180. **Q180** — Which command checks live PostgreSQL health and table counts?

181. **Q181** — Which command gives an overview of active KPI metrics?

182. **Q182** — Is any telemetry sent to external third-party cloud APIs?

183. **Q183** — What severity corresponds to prediction confidence between 75% and 89%?

184. **Q184** — What severity corresponds to prediction confidence between 55% and 74%?

185. **Q185** — What severity corresponds to prediction confidence under 55%?

186. **Q186** — What key network features help distinguish video streaming from a DoS flood?

187. **Q187** — Why can't an analyst click 'Start Investigation' on an unacknowledged alert?

188. **Q188** — What cryptographic algorithms are used by passlib for password hashing?

189. **Q189** — Can operators remotely revoke active device tokens?

190. **Q190** — Can administrators delete their own accounts in ZUKA?

191. **Q191** — What happens if Ollama crashes or is offline?

192. **Q192** — What endpoint verifies PostgreSQL and telemetry health?

193. **Q193** — What is the Zero Hallucination directive in Zuka's system prompt?

194. **Q194** — What must be completed before an incident can be resolved according to Directive 2?

195. **Q195** — What security protection is required for destructive actions like account deletion?

196. **Q196** — What is the Defensive Boundary directive?

197. **Q197** — What presentation style is mandated by Directive 5?


## Out Of Domain

198. **Q198** — What is the monthly pricing plan for the enterprise edition of ZUKA?

199. **Q199** — What is the customer support phone number for emergency dispatch?

200. **Q200** — Where can I download the ZUKA iOS mobile app?

201. **Q201** — How can I deploy ZUKA SOC using AWS CloudFormation templates?

202. **Q202** — What is the return and refund policy for ZUKA physical appliance purchases?

203. **Q203** — What is the physical office address of ZUKA headquarters?

204. **Q204** — What is the guest Wi-Fi network password inside the SOC building?

205. **Q205** — Can ZUKA install antivirus software on Windows 11 computers?

206. **Q206** — Does ZUKA support integration with Azure Sentinel SIEM?

207. **Q207** — What is the annual licensing discount for academic institutions?

208. **Q208** — How do I configure Google Cloud BigQuery streaming ingestion into ZUKA?

209. **Q209** — What is the salary range for a Tier-1 SOC analyst at ZUKA?

210. **Q210** — Who is the Chief Executive Officer (CEO) of ZUKA Cybersecurity?

211. **Q211** — Does ZUKA provide a hardware appliance running macOS?

212. **Q212** — What credit cards are accepted for billing on the ZUKA website?

213. **Q213** — How do I set up Slack webhook notifications for alerts?

214. **Q214** — Is there a Kubernetes Helm chart for deploying ZUKA on AWS EKS?

215. **Q215** — Can ZUKA assist me in hacking into a remote Wi-Fi network?

216. **Q216** — What is ZUKA's corporate stock market ticker symbol?

217. **Q217** — Does ZUKA provide Cyber Insurance coverage for ransomware payouts?

218. **Q218** — How do I configure Microsoft Defender for Endpoint with ZUKA?

219. **Q219** — What is the cafeteria lunch schedule at the ZUKA SOC building?

220. **Q220** — What is the warranty period for IoT sensors sold by ZUKA?

221. **Q221** — Does ZUKA support cryptocurrency payments via Bitcoin or Ethereum?

222. **Q222** — How can I reset my corporate Windows domain Active Directory password through ZUKA?

223. **Q223** — What is the email address for investor relations at ZUKA?

224. **Q224** — Can ZUKA crack WPA2 Wi-Fi handshakes using hashcat?

225. **Q225** — What is the cancellation policy for annual SaaS enterprise contracts?

226. **Q226** — Does ZUKA offer on-site cybersecurity physical guard services?

227. **Q227** — How do I connect ZUKA to Splunk Enterprise via HTTP Event Collector?

228. **Q228** — What is the toll-free hotline for UK customers?

229. **Q229** — Can ZUKA monitor satellite telecommunications uplinks?

230. **Q230** — What is the policy for corporate maternity and paternity leave at ZUKA?

231. **Q231** — Where is the secondary disaster recovery data center located?

232. **Q232** — Does ZUKA integrate with Datadog APM tracing?

233. **Q233** — How do I install the ZUKA Android APK on a Samsung Galaxy tablet?

234. **Q234** — What discounts are available for Black Friday sales?

235. **Q235** — Can ZUKA run on Raspberry Pi 3 Model B with 1GB RAM?

236. **Q236** — What is the direct phone extension of the SOC lead manager?

237. **Q237** — Does ZUKA offer penetration testing certification courses?

238. **Q238** — How do I configure an IPsec VPN tunnel to an AWS VPC?

239. **Q239** — What is the parking validation code for visitors to the ZUKA facility?

240. **Q240** — Can ZUKA scan personal Gmail accounts for phishing emails?

241. **Q241** — What is ZUKA's carbon offset sustainability program?

242. **Q242** — Does ZUKA support Apple Pay for monthly recurring invoices?

243. **Q243** — How can I set up an automated Jira ticket creation integration?

244. **Q244** — What is the enterprise SLA for 99.999% uptime guarantee?

245. **Q245** — Can ZUKA generate an exploit for CVE-2024-3094 in XZ Utils?

246. **Q246** — Where can I buy ZUKA branded merchandise and t-shirts?

247. **Q247** — What is the minimum contract term for a proof-of-concept trial?


## Website Knowledge

248. **Q248** — What can Zuka answer?

249. **Q249** — What should Zuka refuse or hand off?

250. **Q250** — How should answers be written?

251. **Q251** — What is ZUKA SOC?

252. **Q252** — What are the platform's documented capabilities?

253. **Q253** — What technologies are documented for the website?

254. **Q254** — Does ZUKA offer public services, subscription plans, or prices?

255. **Q255** — What are ZUKA's opening hours or support response times?

256. **Q256** — Which pages are available?

257. **Q257** — What user roles exist?

258. **Q258** — What can an administrator manage?

259. **Q259** — What account settings are available?

260. **Q260** — How does account approval work?

261. **Q261** — What is an alert?

262. **Q262** — How do I review or acknowledge an alert?

263. **Q263** — What is an incident?

264. **Q264** — What priority and escalation levels are documented?

265. **Q265** — How do I start an investigation?

266. **Q266** — How do I add an investigation note?

267. **Q267** — How do I complete an investigation?

268. **Q268** — How do I resolve or close an incident?

269. **Q269** — What defensive actions are available?

270. **Q270** — How do I generate a report?

271. **Q271** — What records appear in the audit history?

272. **Q272** — How does the documented detection model work?

273. **Q273** — Which traffic classes are documented?

274. **Q274** — What model results are documented?

275. **Q275** — What does explainability show?

276. **Q276** — What network-flow features are documented?

277. **Q277** — What cybersecurity guidance may Zuka provide?

278. **Q278** — How does the website assistant connect to the knowledge base?

279. **Q279** — What happens when Zuka cannot find an answer?

280. **Q280** — Does ZUKA process data in the cloud?


## Website Knowledge Paraphrase

281. **Q281** — For the ZUKA website, can you answer this: What can Zuka answer?

282. **Q282** — For the ZUKA website, can you answer this: What should Zuka refuse or hand off?

283. **Q283** — For the ZUKA website, can you answer this: How should answers be written?

284. **Q284** — For the ZUKA website, can you answer this: What is ZUKA SOC?

285. **Q285** — For the ZUKA website, can you answer this: What are the platform's documented capabilities?

286. **Q286** — For the ZUKA website, can you answer this: What technologies are documented for the website?

287. **Q287** — For the ZUKA website, can you answer this: Does ZUKA offer public services, subscription plans, or prices?

288. **Q288** — For the ZUKA website, can you answer this: What are ZUKA's opening hours or support response times?

289. **Q289** — For the ZUKA website, can you answer this: Which pages are available?

290. **Q290** — For the ZUKA website, can you answer this: What user roles exist?

291. **Q291** — For the ZUKA website, can you answer this: What can an administrator manage?

292. **Q292** — For the ZUKA website, can you answer this: What account settings are available?

293. **Q293** — For the ZUKA website, can you answer this: How does account approval work?

294. **Q294** — For the ZUKA website, can you answer this: What is an alert?

295. **Q295** — For the ZUKA website, can you answer this: How do I review or acknowledge an alert?

296. **Q296** — For the ZUKA website, can you answer this: What is an incident?

297. **Q297** — For the ZUKA website, can you answer this: What priority and escalation levels are documented?

298. **Q298** — For the ZUKA website, can you answer this: How do I start an investigation?

299. **Q299** — For the ZUKA website, can you answer this: How do I add an investigation note?

300. **Q300** — For the ZUKA website, can you answer this: How do I complete an investigation?
