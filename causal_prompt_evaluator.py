import anthropic
import base64
import os
import re
import json
import datetime
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

class CausalPromptEvaluator:
    def __init__(self, api_key: str):
        """Initialize with Claude API key."""
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Base rubric questions
        self.rubric = [
            "Describe the subject's initial position and surroundings.",
            "Detail the subject's movement and direction.",
            "Identify interactions with physical elements.",
            "Observe background activity.",
            "Describe facial expressions and body language.",
            "Explain environmental progression.",
            "Comment on camera perspective and awareness.",
            "Describe final position and departure.",
            "Comment on video quality and disturbances.",
            "Construct event narrative."
        ]

    def encode_image(self, image_path: str) -> str:
        """Encode image file to base64."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            print(f"Error encoding image {image_path}: {e}")
            return None

    def get_frames(self, frames_dir: str, max_frames: int = 20) -> List[Dict[str, Any]]:
        """Extract and process frames."""
        try:
            # Get all frame files from the directory
            frame_files = [f for f in os.listdir(frames_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

            if not frame_files:
                print(f"No valid image files found in {frames_dir}")
                return []

            # Sort frames numerically (assuming files are named with frame numbers)
            def extract_number(filename):
                numbers = re.findall(r'\d+', filename)
                return int(numbers[0]) if numbers else 0

            frame_files.sort(key=extract_number)

            # Limit total number of frames if needed
            if len(frame_files) > max_frames:
                # Take evenly spaced frames
                step = len(frame_files) // max_frames
                selected_frames = frame_files[::step][:max_frames]
            else:
                selected_frames = frame_files

            # Process selected frames
            processed_frames = []
            for frame_file in selected_frames:
                frame_path = os.path.join(frames_dir, frame_file)
                encoded_content = self.encode_image(frame_path)
                if encoded_content:
                    processed_frames.append({
                        "frame_id": extract_number(frame_file),
                        "filename": frame_file,
                        "content": encoded_content
                    })
                else:
                    print(f"Skipping frame {frame_file} due to encoding error")

            return processed_frames

        except Exception as e:
            print(f"Error in frame processing: {e}")
            return []

    def causal_trace_prompt(self, question: str, template: str = None) -> str:
        """Generate a prompt based on the provided template or default CausalTrace."""
        if template:
            # Replace variables in the template
            return template.replace("{question}", question)
        else:
            # Default CausalTrace prompt
            return (
                f"Analyze the video frames to answer: {question}. "
                "Use the CausalTrace method: "
                "1. Observe raw events without preconceptions. "
                "2. Identify primary actions and their direct effects. "
                "3. Trace backward to confirm the cause precedes the effect. "
                "4. Consider counterfactuals: would the effect occur without the cause? "
                "5. Rule out confounding factors and coincidental correlations. "
                "Provide a clear explanation of the causal chain, avoiding assumptions or statistical correlations."
            )

    def prepare_evaluation_message(self, frames: List[Dict[str, Any]], 
                                  rubric_question: str, 
                                  template: str = None) -> Dict[str, Any]:
        """Prepare a message for evaluating a single rubric question."""
        # Generate prompt
        prompt = self.causal_trace_prompt(rubric_question, template)

        # Prepare message for Claude API
        message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }

        # Add frames as content
        for frame in frames:
            message["content"].append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame["content"]
                }
            })

        return message
    
    def send_api_request(self, message: Dict[str, Any], model: str = "claude-3-7-sonnet-20250219") -> Tuple[Optional[Any], Optional[str]]:
        """Send the prepared message to Claude API and get response."""
        try:
            print(f"Sending request to {model}...")
            
            response = self.client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[message]
            )
            
            print("Response received successfully!")
            return response, None
            
        except Exception as e:
            error_msg = str(e)
            print(f"API call failed: {error_msg}")
            return None, error_msg

    def evaluate_rubric_question(self, 
                               frames: List[Dict[str, Any]], 
                               rubric_question: str, 
                               template: str = None,
                               model: str = "claude-3-7-sonnet-20250219") -> Dict[str, Any]:
        """Evaluate prompt performance on a single rubric question."""
        print(f"Evaluating: {rubric_question}")
        
        # Prepare message
        message = self.prepare_evaluation_message(frames, rubric_question, template)
        
        # Send API request
        response, error = self.send_api_request(message, model)
        
        if response:
            return {
                "question": rubric_question,
                "response": response.content[0].text,
                "error": None
            }
        else:
            return {
                "question": rubric_question,
                "response": None,
                "error": error
            }

    def run_full_evaluation(self, 
                          frames_dir: str, 
                          template_id: str = None,
                          template_content: str = None,
                          model: str = "claude-3-7-sonnet-20250219") -> Dict[str, Any]:
        """Evaluate prompt performance across all rubric questions."""
        print("Starting full rubric evaluation...")
        
        # Generate a unique ID for this evaluation
        eval_id = str(uuid.uuid4())
        
        # Get frames
        frames = self.get_frames(frames_dir)
        if not frames:
            return {
                "id": eval_id,
                "error": "No valid frames found", 
                "results": []
            }
        
        print(f"Using {len(frames)} frames for evaluation")
        
        # Evaluate each rubric question
        evaluation_results = []
        for i, question in enumerate(self.rubric):
            print(f"\nEvaluating question {i+1}/{len(self.rubric)}")
            result = self.evaluate_rubric_question(frames, question, template_content, model)
            evaluation_results.append(result)
            
            # Brief pause between requests to avoid rate limiting
            time.sleep(2)
        
        # Compile final report
        current_time = datetime.datetime.now()
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        full_evaluation = {
            "id": eval_id,
            "timestamp": timestamp,
            "frames_analyzed": len(frames),
            "frames_path": frames_dir,
            "template_id": template_id,
            "model": model,
            "results": evaluation_results
        }
        
        return full_evaluation
    
    def save_evaluation(self, evaluation: Dict[str, Any], output_dir: str = "results"):
        """Save evaluation results to JSON file."""
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename using the evaluation ID
            output_path = os.path.join(output_dir, f"{evaluation['id']}.json")
            
            # Save as JSON
            with open(output_path, 'w') as f:
                json.dump(evaluation, f, indent=2)
                
            print(f"Evaluation saved to {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error saving evaluation: {e}")
            return None

if __name__ == "__main__":
    print("This module is intended to be imported, not run directly.")
