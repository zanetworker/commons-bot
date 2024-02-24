import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from llama_hub.youtube_transcript import YoutubeTranscriptReader

load_dotenv()

class EnvironmentConfig:
    def __init__(self):
        self.load_env()

    def load_env(self):
        load_dotenv()
        self.qd_endpoint = os.getenv("QD_ENDPOINT")
        self.qd_api_key = os.getenv("QD_API_KEY")

        if not self.qd_endpoint and not self.qd_api_key:
            raise ValueError("QD_ENDPOINT and QD_API_KEY are required")
               
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")

        if not self.slack_bot_token:
            raise ValueError("SLACK_BOT_TOKEN is required")
        if not self.slack_signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET is required")
        
        self.graph_signal_api_key = os.getenv("GRAPH_SIGNAL_API_KEY")

        if not self.graph_signal_api_key:
            raise ValueError("GRAPH_SIGNAL_API_KEY is required")
        
    
class QdrantClientManager:
    def __init__(self, config):
        self.config = config
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if self.config.qd_endpoint and self.config.qd_api_key:
                self._client = QdrantClient(url=self.config.qd_endpoint, api_key=self.config.qd_api_key)
            else:
                self._client = QdrantClient(path="./qdrant_data")
        return self._client
    

class YouTubeLoader:
    def __init__(self):
        # self.file_path = file_path
        self._ytlinks = None
        self._yttranscripts = None

    def _load_youtube_links(self):
        with open(self.file_path, 'r') as file:
            ytlinks = file.readlines()
        return ytlinks

    def _load_youtube_transcripts(self, ytlinks):
        loader = YoutubeTranscriptReader()
        return loader.load_data(ytlinks=ytlinks)

    # define property for ytlinks
    @property
    def ytlinks(self):
        if self._ytlinks is None:
            try: 
                self._ytlinks = self._load_youtube_links()
            except Exception as e:
                self._ytlinks =  ytlinks = [
                'https://youtu.be/ZxvbQbT_wkc?feature=shared',   
                'https://www.youtube.com/watch?v=RzxzY1dluvo',
                'https://www.youtube.com/watch?v=ZTsgcnxQyw4',
                'https://www.youtube.com/watch?v=m-p7jmXoQdk', 
                'https://www.youtube.com/watch?v=6PZfKufNisM',
                'https://www.youtube.com/watch?v=-Ma4FBOtdbo',
                'https://www.youtube.com/watch?v=eEwQeLns_hU',
                'https://www.youtube.com/watch?v=njscOv2wJeA',
                'https://www.youtube.com/watch?v=i5BmIJSaduk',
                'https://www.youtube.com/watch?v=4_3B0lAsXWQ',
                'https://www.youtube.com/watch?v=ZOKJWp3GfRs',
                'https://www.youtube.com/watch?v=iLaMDtf7hqk',
                'https://www.youtube.com/watch?v=E5gnj61MyhM',
                'https://www.youtube.com/watch?v=0ZnzZpU7K8w',
                'https://www.youtube.com/watch?v=NdZ8zuqaT8U',
                'https://www.youtube.com/watch?v=8L-IdpEUGxU',
                'https://www.youtube.com/watch?v=6Os9JMNCDXY',
                'https://www.youtube.com/watch?v=Nw3eMHWDCUc',
                'https://www.youtube.com/watch?v=M2rdwyFzx2M',
                'https://www.youtube.com/watch?v=HDkwtVbuL1w',
                'https://www.youtube.com/watch?v=IMs9gdXXB1s',
                'https://www.youtube.com/watch?v=K1KNXzOTK-0',
                'https://www.youtube.com/watch?v=WyA_hts7XMs',
                'https://www.youtube.com/watch?v=3dkyD3u6iP4',
                'https://www.youtube.com/watch?v=n3epPdiOOOM',
                'https://www.youtube.com/watch?v=TJPOR98MKV8',
                'https://www.youtube.com/watch?v=pKEi_o2mA40',
                'https://www.youtube.com/watch?v=qNgtxU5XOrg',
                'https://www.youtube.com/watch?v=aVq69JzC6jM',
                'https://www.youtube.com/watch?v=_3IfYLb_bbE', 
                'https://www.youtube.com/watch?v=3vjOCOLXExQ',
                'https://www.youtube.com/watch?v=zcO2qR2dbdo',
                'https://www.youtube.com/watch?v=RCwcEZtba4E',
                'https://www.youtube.com/watch?v=bIruzpvRe74',
                'https://www.youtube.com/watch?v=9YLMf-d_Kqk',
                'https://www.youtube.com/watch?v=lojstGGfB3E',
                'https://www.youtube.com/watch?v=M6bqUfIecKA',
                'https://www.youtube.com/watch?v=lQHMRXGB_pY',
                'https://www.youtube.com/watch?v=RYP6ZntTby4',
                'https://www.youtube.com/watch?v=eT5Dz3fziQY',
                'https://www.youtube.com/watch?v=Q05O1H0UxaI',
                'https://www.youtube.com/watch?v=1082Lke8rz0',
                'https://www.youtube.com/watch?v=PTo2soO20Fs',
                'https://www.youtube.com/watch?v=L4tk3b5uTEI',
                'https://www.youtube.com/watch?v=tnmoGz9JBQA',
                'https://www.youtube.com/watch?v=nJJdfw_ymfU',
                'https://www.youtube.com/watch?v=fJXRHsxLnI4',
                'https://www.youtube.com/watch?v=tissYjujjiE',
                'https://www.youtube.com/watch?v=mpzr_HOPSkE',
                'https://www.youtube.com/watch?v=7rl1OVUlx1k',
                'https://www.youtube.com/watch?v=MKSzBZ3-mvQ',
                'https://www.youtube.com/watch?v=csgCyfnq7qs',
                'https://www.youtube.com/watch?v=N4tt8_VP1o0',
                'https://www.youtube.com/watch?v=yl5MtiQqbsQ',
                'https://www.youtube.com/watch?v=tVSPTrf_JXU',
                'https://www.youtube.com/watch?v=r75lTd_lKyQ',
                'https://www.youtube.com/watch?v=AKPB2IQ-ew0',
                'https://www.youtube.com/watch?v=ZYXAfCCEKS0',
                'https://www.youtube.com/watch?v=JcdB55yLGbg',
                'https://www.youtube.com/watch?v=lHkZOu0EMys',
                'https://www.youtube.com/watch?v=MYyikxV0l-o',
                'https://www.youtube.com/watch?v=OqGfwy0d7b8',
                'https://www.youtube.com/watch?v=e86IbJaPIFQ',
                'https://www.youtube.com/watch?v=PuMA5OrJtXo',
                'https://www.youtube.com/watch?v=Kk5SRhxSCmM',
                'https://www.youtube.com/watch?v=aELiz-g12dk',
                'https://www.youtube.com/watch?v=Gf0d7q4ZEfw',
                'https://www.youtube.com/watch?v=XO2k1oqy9qU',
                'https://www.youtube.com/watch?v=5a377Rda79U',
                'https://www.youtube.com/watch?v=dIG3gLmDRXg',
                'https://www.youtube.com/watch?v=TqpNf1xt2ZQ',
                'https://www.youtube.com/watch?v=0bqwVuSV9ho',
                'https://www.youtube.com/watch?v=UejmEiAptFE',
                'https://www.youtube.com/watch?v=_Gft7jkmxTI',
                'https://www.youtube.com/watch?v=8_6MQdtd2ww',
                'https://www.youtube.com/watch?v=fe-OhqT_kxA',
                'https://www.youtube.com/watch?v=SKbA4b2JZOg',
                'https://www.youtube.com/watch?v=anaB7pBL9uU',
                'https://www.youtube.com/watch?v=cJUunrXVT50',
                'https://www.youtube.com/watch?v=OXPkHNoWOec',
                'https://www.youtube.com/watch?v=1KNFnQG2b5w',
                'https://www.youtube.com/watch?v=Mz4R4iDDm0M',
                'https://www.youtube.com/watch?v=HfsJqqjmiZo',
                'https://www.youtube.com/watch?v=1ddxwZWSgtY',
                'https://www.youtube.com/watch?v=J_c2_yBJ5bs',
                'https://www.youtube.com/watch?v=KizNQTpRA2A',
                'https://www.youtube.com/watch?v=3S855TdwhH4',
                'https://www.youtube.com/watch?v=_Cug1C744Ug',
                'https://www.youtube.com/watch?v=FZNcX2SosjU',
                'https://www.youtube.com/watch?v=tfnHap8K9cM',
                'https://www.youtube.com/watch?v=kBmLBHc16eA',
                'https://www.youtube.com/watch?v=YF3S9WqWZpU',
                'https://www.youtube.com/watch?v=KQmiM06tsEE',
                'https://www.youtube.com/watch?v=S6Obo7pw6p4',
                'https://www.youtube.com/watch?v=Tt0RlJYrcC8',
                'https://www.youtube.com/watch?v=p1UNdLqJ9sQ',
                'https://www.youtube.com/watch?v=lsltHGUZ6nE',
                'https://www.youtube.com/watch?v=aq1VFOiLi_0',
                'https://www.youtube.com/watch?v=v6s5KznHULs',
                'https://www.youtube.com/watch?v=4L0R6Ews5uY',
                'https://www.youtube.com/watch?v=b-QtgBEgt-c',
                'https://www.youtube.com/watch?v=U1e7nRA843E',
                'https://www.youtube.com/watch?v=mvcPzQHpUW0',
                'https://www.youtube.com/watch?v=vae2Wx5LLYg',
                'https://www.youtube.com/watch?v=vQUhtN0Vjro',
                'https://www.youtube.com/watch?v=4_Duwdhi1aA',
                'https://www.youtube.com/watch?v=c2suFsA4Evw',
                'https://www.youtube.com/watch?v=6BD3pknWwvY',
                'https://www.youtube.com/watch?v=T1YSBXP9T9s',
                'https://www.youtube.com/watch?v=szEz9Ocnao0',
                'https://www.youtube.com/watch?v=dJe857oQV4Q',
                'https://www.youtube.com/watch?v=LrIvFQaq_Zo',
                'https://www.youtube.com/watch?v=awgmTOLxYOE',
                'https://www.youtube.com/watch?v=X8eg0RuGYG0',
                'https://www.youtube.com/watch?v=-MNGRqubMw4',
                'https://www.youtube.com/watch?v=Nwz2aGoqjE0',
                'https://www.youtube.com/watch?v=y0_-CAcRnUk',
                'https://www.youtube.com/watch?v=o-qae0vJ3Aw',
                'https://www.youtube.com/watch?v=kMnIGSb3T8w',
                'https://www.youtube.com/watch?v=mWdglzUb6vY',
                'https://www.youtube.com/watch?v=6YMfzqHXfqg',
                'https://www.youtube.com/watch?v=ZIKq0W9z31I',
                'https://www.youtube.com/watch?v=-PCLnEoIZp4',
                'https://www.youtube.com/watch?v=i5wd_qZdc8Y',
                'https://www.youtube.com/watch?v=SVk_IIT0O2E',
                'https://www.youtube.com/watch?v=SESq3OZxNBY',
                'https://www.youtube.com/watch?v=DhpDqa7oxzI',
                'https://www.youtube.com/watch?v=fnH60GhaZ1w',
                'https://www.youtube.com/watch?v=5cueeNm667U',
            ]
        return self._ytlinks
    
    # define property for yttranscripts
    @property
    def yttranscripts(self):
        if self._yttranscripts is None:
            self._yttranscripts = self._load_youtube_transcripts(self.ytlinks)
        return self._yttranscripts
    