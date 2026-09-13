# ---------------------------------------------------------------------------

class InferenceClient:
    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        return ""


class Example(BaseModel):
    message: str
    choices: List[Dict[str, str]] = Field(default_factory=list)
    choice: str
    reasoning: str

    model_config = {"arbitrary_types_allowed": True}


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = []
    default: Optional[str] = None


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = True
    voters: int = 1

    model_config = {"arbitrary_types_allowed": True}

    def set_attrs(self) -> None:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        counter = Counter(string_list)
        return counter.most_common(1)[0][0]

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        if self.inference_client is None:
            return ""
        prompt = str(generation_input)
        result = await self.inference_client.generate(
            prompt=prompt, system=self.system_description
        )
        return result

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"next_node": None}

        input_data = None
        if self.input_var:
            input_data = await cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            vote = await self.gen(input_data, cache)
            votes.append(vote)

        chosen = self.most_common_string(votes)

        if self.flow_config.decisions:
            for decision in self.flow_config.decisions:
                if decision.next_node == chosen:
                    return {"next_node": decision.next_node}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default}

        return {"next_node": None}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# Update forward references
# ---------------------------------------------------------------------------

ModuleConfig.model_rebuild()
AgentModule.model_rebuild()
CompositeModule.model_rebuild()
Node.model_rebuild()
FlowControlModule.model_rebuild()
Agent.model_rebuild()
AgentDirectedFlowControl.model_rebuild()
