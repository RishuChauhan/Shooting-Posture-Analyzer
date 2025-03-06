#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Posture Analysis Module using Fuzzy Logic

This module analyzes shooting posture using fuzzy logic to provide
a posture score and actionable feedback.

Author: Claude
Date: March 6, 2025
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import logging
from typing import Dict, List, Tuple, Optional, Union

# Initialize logger
logger = logging.getLogger(__name__)

class PostureAnalyzer:
    """
    Analyzes shooting posture using fuzzy logic.
    Provides scoring and feedback based on joint angles.
    """
    
    def __init__(self):
        """
        Initialize the posture analyzer with fuzzy logic system.
        Sets up membership functions and rules for posture evaluation.
        """
        # Initialize fuzzy logic system
        self._init_fuzzy_system()
        
        # Feedback messages based on posture
        self.feedback_rules = {
            'knees': {
                'low': "Straighten your knees slightly, they're too bent",
                'high': "Bend your knees slightly for better stability"
            },
            'hips': {
                'low': "Adjust your hip position to be more upright",
                'high': "Lower your hips slightly for better alignment"
            },
            'left_shoulder': {
                'low': "Raise your left shoulder more to support the rifle",
                'high': "Lower your left shoulder slightly for better control"
            },
            'right_shoulder': {
                'low': "Raise your right shoulder slightly",
                'high': "Lower your right shoulder closer to your body"
            },
            'left_elbow': {
                'low': "Raise your left elbow more to support the rifle",
                'high': "Lower your left elbow slightly for better stability"
            },
            'right_elbow': {
                'low': "Bend your right elbow more for proper grip",
                'high': "Extend your right elbow slightly for better control"
            },
            'wrists': {
                'low': "Straighten your wrists more for consistent support",
                'high': "Relax your wrists slightly for better control"
            },
            'neck': {
                'low': "Tilt your head forward slightly to align with sights",
                'high': "Raise your head slightly to improve sight alignment"
            }
        }
        
        # Ideal angles for shooting stance
        self.ideal_angles = {
            'knees': 172.5,  # Slightly bent (170°-175°)
            'hips': 180.0,   # Straight (175°-185°)
            'left_shoulder': 45.0,  # Raised to support rifle (30°-60°)
            'right_shoulder': 15.0,  # Closer to body (0°-30°)
            'left_elbow': 75.0,  # Bent to support rifle (60°-90°)
            'right_elbow': 90.0,  # Bent for grip (80°-100°)
            'wrists': 180.0,  # Straight (170°-190°)
            'neck': 12.5,    # Tilted forward (10°-15°)
        }
        
        # Angle ranges (min, max) for each joint
        self.angle_ranges = {
            'knees': (170.0, 175.0),
            'hips': (175.0, 185.0),
            'left_shoulder': (30.0, 60.0),
            'right_shoulder': (0.0, 30.0),
            'left_elbow': (60.0, 90.0),
            'right_elbow': (80.0, 100.0),
            'wrists': (170.0, 190.0),
            'neck': (10.0, 15.0),
        }
        
        # Weight of each joint in the overall posture score
        self.joint_weights = {
            'knees': 0.1,
            'hips': 0.1,
            'left_shoulder': 0.2,
            'right_shoulder': 0.1,
            'left_elbow': 0.2,
            'right_elbow': 0.15,
            'wrists': 0.05,
            'neck': 0.1,
        }
        
        logger.info("PostureAnalyzer initialized")
    
    def _init_fuzzy_system(self):
        """
        Initialize the fuzzy logic control system.
        Sets up antecedents, consequents, and rules.
        """
        # Create antecedents (inputs) for each joint deviation
        self.deviation = ctrl.Antecedent(np.arange(0, 101, 1), 'deviation')
        
        # Create consequent (output) for quality score
        self.quality = ctrl.Consequent(np.arange(0, 101, 1), 'quality')
        
        # Define membership functions for deviation
        self.deviation['small'] = fuzz.trimf(self.deviation.universe, [0, 0, 25])
        self.deviation['medium'] = fuzz.trimf(self.deviation.universe, [0, 25, 50])
        self.deviation['large'] = fuzz.trimf(self.deviation.universe, [25, 50, 75])
        self.deviation['very_large'] = fuzz.trimf(self.deviation.universe, [50, 100, 100])
        
        # Define membership functions for quality
        self.quality['poor'] = fuzz.trimf(self.quality.universe, [0, 0, 30])
        self.quality['fair'] = fuzz.trimf(self.quality.universe, [10, 40, 70])
        self.quality['good'] = fuzz.trimf(self.quality.universe, [40, 70, 90])
        self.quality['excellent'] = fuzz.trimf(self.quality.universe, [70, 100, 100])
        
        # Define rules
        rule1 = ctrl.Rule(self.deviation['small'], self.quality['excellent'])
        rule2 = ctrl.Rule(self.deviation['medium'], self.quality['good'])
        rule3 = ctrl.Rule(self.deviation['large'], self.quality['fair'])
        rule4 = ctrl.Rule(self.deviation['very_large'], self.quality['poor'])
        
        # Create control system
        self.posture_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4])
        self.posture_sim = ctrl.ControlSystemSimulation(self.posture_ctrl)
    
    def analyze_posture(self, joint_angles: Dict[str, float]) -> Dict:
        """
        Analyze posture based on joint angles.
        
        Args:
            joint_angles: Dictionary of measured joint angles
            
        Returns:
            Dictionary containing posture score and feedback
        """
        if not joint_angles:
            return {
                'score': 0,
                'feedback': ["No pose detected"],
                'joint_scores': {},
                'deviations': {}
            }
        
        # Calculate weighted score and generate feedback
        overall_score = 0
        joint_scores = {}
        deviations = {}
        feedback_items = []
        
        # Process each joint
        for joint_name, ideal_angle in self.ideal_angles.items():
            if joint_name not in joint_angles:
                continue
            
            # Get the measured angle
            measured_angle = joint_angles[joint_name]
            
            # Calculate deviation percentage
            min_angle, max_angle = self.angle_ranges[joint_name]
            angle_range = max_angle - min_angle
            
            # Normalize deviation to 0-100 scale
            if measured_angle < min_angle:
                # Below minimum
                deviation_pct = min(100, 100 * (min_angle - measured_angle) / (min_angle * 0.5))
                direction = 'low'
            elif measured_angle > max_angle:
                # Above maximum
                deviation_pct = min(100, 100 * (measured_angle - max_angle) / (max_angle * 0.5))
                direction = 'high'
            else:
                # Within range
                deviation_pct = 0
                direction = None
            
            # Use fuzzy system to evaluate quality based on deviation
            self.posture_sim.input['deviation'] = deviation_pct
            self.posture_sim.compute()
            joint_score = self.posture_sim.output['quality']
            
            # Apply weight to joint score
            weighted_score = joint_score * self.joint_weights[joint_name]
            overall_score += weighted_score
            
            # Store joint score and deviation
            joint_scores[joint_name] = joint_score
            deviations[joint_name] = {
                'percentage': deviation_pct,
                'direction': direction,
                'measured': measured_angle,
                'ideal': ideal_angle
            }
            
            # Add feedback if deviation is significant
            if deviation_pct > 20 and direction:
                feedback_items.append(self.feedback_rules[joint_name][direction])
        
        # If no significant deviations found, add positive feedback
        if not feedback_items:
            feedback_items.append("Great posture! Keep maintaining this stance.")
        
        # Return analysis results
        return {
            'score': overall_score,
            'feedback': feedback_items,
            'joint_scores': joint_scores,
            'deviations': deviations
        }
    
    def get_detailed_analysis(self, joint_angles: Dict[str, float]) -> Dict:
        """
        Provide detailed analysis of posture with specific adjustments needed.
        
        Args:
            joint_angles: Dictionary of measured joint angles
            
        Returns:
            Dictionary containing detailed analysis and adjustment recommendations
        """
        basic_analysis = self.analyze_posture(joint_angles)
        
        # Generate specific adjustment recommendations
        detailed_adjustments = {}
        
        for joint_name, deviation_info in basic_analysis['deviations'].items():
            if deviation_info['direction']:
                measured = deviation_info['measured']
                ideal = deviation_info['ideal']
                difference = abs(measured - ideal)
                
                if difference > 5:  # Only suggest adjustments for significant deviations
                    adjustment = {
                        'current': measured,
                        'target': ideal,
                        'adjust_by': ideal - measured,
                        'instruction': f"Adjust {joint_name.replace('_', ' ')} by {abs(ideal - measured):.1f}° "
                                      f"{'down' if measured > ideal else 'up'}"
                    }
                    detailed_adjustments[joint_name] = adjustment
        
        # Add detailed adjustments to the analysis
        basic_analysis['detailed_adjustments'] = detailed_adjustments
        
        return basic_analysis
    
    def analyze_stability(self, joint_angles_sequence: List[Dict[str, float]]) -> Dict:
        """
        Analyze stability of posture over a sequence of frames.
        
        Args:
            joint_angles_sequence: List of joint angle dictionaries over time
            
        Returns:
            Dictionary containing stability metrics
        """
        if not joint_angles_sequence:
            return {
                'stability_score': 0,
                'variations': {},
                'stable_joints': [],
                'unstable_joints': []
            }
        
        # Calculate variation for each joint across frames
        variations = {}
        stable_joints = []
        unstable_joints = []
        
        # Get list of all joint names
        joint_names = set()
        for angles in joint_angles_sequence:
            joint_names.update(angles.keys())
        
        # Calculate standard deviation for each joint
        for joint in joint_names:
            # Collect all values for this joint
            values = [angles.get(joint, float('nan')) for angles in joint_angles_sequence]
            values = [v for v in values if not np.isnan(v)]
            
            if values:
                # Calculate mean and standard deviation
                mean_value = np.mean(values)
                std_dev = np.std(values)
                
                # Normalize std_dev as percentage of mean
                if mean_value != 0:
                    variation_pct = (std_dev / mean_value) * 100
                else:
                    variation_pct = std_dev * 100
                
                variations[joint] = {
                    'mean': mean_value,
                    'std_dev': std_dev,
                    'variation_pct': variation_pct
                }
                
                # Classify joint as stable or unstable
                if variation_pct < 5:
                    stable_joints.append(joint)
                else:
                    unstable_joints.append(joint)
        
        # Calculate overall stability score (inverse of weighted average variation)
        if variations:
            weighted_variation = 0
            total_weight = 0
            
            for joint, var_info in variations.items():
                if joint in self.joint_weights:
                    weight = self.joint_weights[joint]
                    weighted_variation += var_info['variation_pct'] * weight
                    total_weight += weight
            
            if total_weight > 0:
                avg_variation = weighted_variation / total_weight
                # Convert to 0-100 score (higher is better)
                stability_score = max(0, 100 - avg_variation * 5)
            else:
                stability_score = 0
        else:
            stability_score = 0
        
        return {
            'stability_score': stability_score,
            'variations': variations,
            'stable_joints': stable_joints,
            'unstable_joints': unstable_joints
        }
    
    def generate_session_summary(self, 
                                posture_analyses: List[Dict],
                                stability_analysis: Dict) -> Dict:
        """
        Generate a summary of a shooting session.
        
        Args:
            posture_analyses: List of posture analysis results
            stability_analysis: Stability analysis result
            
        Returns:
            Dictionary containing session summary
        """
        if not posture_analyses:
            return {
                'overall_score': 0,
                'posture_quality': 'N/A',
                'stability': 'N/A',
                'key_strengths': [],
                'areas_to_improve': [],
                'recommendations': []
            }
        
        # Calculate average posture score
        avg_posture_score = np.mean([analysis['score'] for analysis in posture_analyses])
        
        # Get stability score
        stability_score = stability_analysis['stability_score']
        
        # Calculate overall score (70% posture, 30% stability)
        overall_score = 0.7 * avg_posture_score + 0.3 * stability_score
        
        # Determine posture quality category
        if overall_score >= 85:
            posture_quality = "Excellent"
        elif overall_score >= 70:
            posture_quality = "Good"
        elif overall_score >= 50:
            posture_quality = "Fair"
        else:
            posture_quality = "Needs Improvement"
        
        # Determine stability category
        if stability_score >= 85:
            stability_category = "Very Stable"
        elif stability_score >= 70:
            stability_category = "Stable"
        elif stability_score >= 50:
            stability_category = "Moderately Stable"
        else:
            stability_category = "Unstable"
        
        # Identify strengths and areas to improve
        strengths = []
        improvements = []
        
        # Find consistently good joints
        good_joint_scores = {}
        for analysis in posture_analyses:
            for joint, score in analysis['joint_scores'].items():
                if joint not in good_joint_scores:
                    good_joint_scores[joint] = []
                good_joint_scores[joint].append(score)
        
        for joint, scores in good_joint_scores.items():
            avg_score = np.mean(scores)
            if avg_score >= 85:
                joint_name = joint.replace('_', ' ').title()
                strengths.append(f"Strong {joint_name} Position")
        
        # Add stability strengths
        for joint in stability_analysis['stable_joints']:
            joint_name = joint.replace('_', ' ').title()
            if joint_name not in strengths:
                strengths.append(f"Stable {joint_name}")
        
        # Find common feedback items
        feedback_counter = {}
        for analysis in posture_analyses:
            for feedback in analysis['feedback']:
                if feedback not in feedback_counter:
                    feedback_counter[feedback] = 0
                feedback_counter[feedback] += 1
        
        # Sort feedback by frequency
        sorted_feedback = sorted(feedback_counter.items(), 
                                key=lambda x: x[1], 
                                reverse=True)
        
        # Add top 3 feedback items to improvements
        for feedback, count in sorted_feedback[:3]:
            if "Great posture" not in feedback:  # Skip positive feedback
                improvements.append(feedback)
        
        # Add unstable joints to improvements
        for joint in stability_analysis['unstable_joints']:
            joint_name = joint.replace('_', ' ').title()
            improvements.append(f"Improve {joint_name} Stability")
        
        # Generate recommendations
        recommendations = []
        
        if "Needs Improvement" in posture_quality or "Fair" in posture_quality:
            recommendations.append("Focus on basic stance fundamentals before proceeding.")
            
        if stability_category == "Unstable" or stability_category == "Moderately Stable":
            recommendations.append("Practice holding your position steady for longer periods.")
            
        if improvements:
            for improvement in improvements[:2]:  # Top 2 improvements
                if "shoulder" in improvement.lower():
                    recommendations.append("Try shoulder strengthening exercises.")
                elif "elbow" in improvement.lower():
                    recommendations.append("Practice elbow positioning with a training aid.")
                elif "knee" in improvement.lower() or "hip" in improvement.lower():
                    recommendations.append("Work on lower body stability through balance exercises.")
                    
        if not recommendations:
            recommendations.append("Continue practicing to maintain your excellent form.")
            
        # Return summary
        return {
            'overall_score': overall_score,
            'posture_quality': posture_quality,
            'stability': stability_category,
            'key_strengths': strengths[:3],  # Top 3 strengths
            'areas_to_improve': improvements[:3],  # Top 3 areas to improve
            'recommendations': recommendations
        }