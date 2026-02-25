import json

class FlowEngine:
    def __init__(self, flows, context=None):
        self.flows = flows
        self.context = context or {}
        self.active_flow = None
        self.steps = {}
        self.current_step_id = None

    def start_flow(self, flow_id):
        flow = self.flows.get(flow_id)
        if not flow:
            return "Sorry I don't have troubleshooting steps for that."
        self.active_flow = flow
        # Map steps for fast lookup
        self.steps = {step["id"]: step for step in flow["steps"]}
        self.current_step_id = flow["start"]
        return self._ask_current_question()

    def handle_input(self, user_input):
        if not self.active_flow:
            return None

        step = self._get_step(self.current_step_id)
        if not step:
            self._reset()
            return "Something went wrong with the troubleshooting flow."

        answer = user_input.strip().lower()

        if step["type"] == "yes_no":
            if answer in ("yes", "y"):
                return self._next_step(step.get("yes"))
            elif answer in ("no", "n"):
                return self._next_step(step.get("no"))
            else:
                return "Please answer yes or no"

        elif step["type"] == "ack":
            return self._next_step(step.get("next"))

        else:
            return "Unsupported step type"

    def _next_step(self, next_step):
        if not next_step:
            self._reset()
            return "Flow ended."

        # If next_step is a dict
        if isinstance(next_step, dict):
            response = self._render_text(next_step.get("response", ""))
            if next_step.get("end"):
                self._reset()
                return response
            # Move to next step if it exists, otherwise end
            self.current_step_id = next_step.get("next")
            if self.current_step_id:
                return response + "\n" + self._ask_current_question()
                
            else:
                return response

        # If next_step is a string (step ID)
        self.current_step_id = next_step
        return self._ask_current_question()

    def _ask_current_question(self):
        step = self._get_step(self.current_step_id)
        if not step:
            return "Flow ended."
        
        question = step.get("question", "")
        return self._render_text(question)

    def _get_step(self, step_id):
        if not step_id:
            return None
        return self.steps.get(step_id)
    
    def _render_text(self, text):
        if not text:
            return text
        for key, value in self.context.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def _reset(self):
        self.active_flow = None
        self.steps = {}
        self.current_step_id = None