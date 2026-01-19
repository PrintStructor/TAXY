import cv2
import numpy as np
import time
import os

class NozzleDetector:
    def __init__(self, model_path, conf_thres=0.25, iou_thres=0.45):
        """
        Inizializza il rilevatore di ugelli.
        Supporta modelli .tflite (consigliato per Orange Pi) e .onnx.
        """
        self.model_path = model_path
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.ext = os.path.splitext(model_path)[1].lower()
        
        print(f"Caricamento modello: {model_path}...")
        
        if self.ext == '.tflite':
            try:
                import tflite_runtime.interpreter as tflite
            except ImportError:
                try:
                    import tensorflow.lite as tflite
                except ImportError:
                    raise ImportError("Errore: Installa 'tflite-runtime' o 'tensorflow' per usare modelli .tflite")
            
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            # Ottieni dimensioni input (es. 640x640)
            self.input_shape = self.input_details[0]['shape']
            self.input_height = self.input_shape[1]
            self.input_width = self.input_shape[2]
            self.input_type = self.input_details[0]['dtype']
            
        elif self.ext == '.onnx':
            try:
                import onnxruntime as ort
            except ImportError:
                raise ImportError("Errore: Installa 'onnxruntime' per usare modelli .onnx")
                
            self.session = ort.InferenceSession(model_path)
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.input_height = 640 # Default YOLOv8
            self.input_width = 640
            
        else:
            raise ValueError(f"Formato modello non supportato: {self.ext}. Usa .tflite o .onnx")
            
        print(f"Modello caricato. Input size: {self.input_width}x{self.input_height}")

    def preprocess(self, image):
        """
        Ridimensiona e normalizza l'immagine per il modello.
        """
        self.img_height, self.img_width = image.shape[:2]
        
        # Resize mantenendo aspect ratio (letterbox)
        scale = min(self.input_width / self.img_width, self.input_height / self.img_height)
        new_w = int(self.img_width * scale)
        new_h = int(self.img_height * scale)
        
        resized = cv2.resize(image, (new_w, new_h))
        
        # Padding per arrivare a 640x640
        canvas = np.full((self.input_height, self.input_width, 3), 114, dtype=np.uint8)
        
        # Centra l'immagine
        top = (self.input_height - new_h) // 2
        left = (self.input_width - new_w) // 2
        canvas[top:top+new_h, left:left+new_w] = resized
        
        # Normalizzazione (0-255 -> 0.0-1.0)
        input_data = canvas.astype(np.float32) / 255.0
        
        # Gestione formato Input
        if self.ext == '.tflite':
            # Controlla se il modello vuole NHWC (1, 640, 640, 3) o NCHW (1, 3, 640, 640)
            if self.input_shape[-1] == 3: # NHWC
                input_data = np.expand_dims(input_data, axis=0)
            else: # NCHW
                input_data = input_data.transpose((2, 0, 1))
                input_data = np.expand_dims(input_data, axis=0)
        else:
            # ONNX standard è NCHW
            input_data = input_data.transpose((2, 0, 1))
            input_data = np.expand_dims(input_data, axis=0)
        
        return input_data, scale, top, left

    def infer(self, image):
        """
        Esegue l'inferenza sull'immagine.
        Ritorna una lista di dizionari: [{'box': [x1, y1, x2, y2], 'score': float, 'class_id': int}, ...]
        """
        input_data, scale, pad_top, pad_left = self.preprocess(image)
        
        start_time = time.time()
        
        if self.ext == '.tflite':
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        elif self.ext == '.onnx':
            output_data = self.session.run([self.output_name], {self.input_name: input_data})[0]
            
        inference_time = (time.time() - start_time) * 1000
        
        # Post-processing YOLOv8
        # Output shape: (1, 4 + num_classes, 8400) -> (1, 5, 8400) per 1 classe
        output_data = np.squeeze(output_data) # (5, 8400)
        output_data = output_data.T # (8400, 5)
        
        boxes = []
        scores = []
        class_ids = []
        
        # Filtra per confidenza
        # Row format: [x_center, y_center, width, height, class1_conf, class2_conf, ...]
        
        # Per YOLOv8 detection, le prime 4 colonne sono bbox, le restanti sono le classi
        # Se abbiamo 1 classe, shape è (8400, 5)
        
        for i in range(output_data.shape[0]):
            row = output_data[i]
            classes_scores = row[4:]
            class_id = np.argmax(classes_scores)
            score = classes_scores[class_id]
            
            if score > self.conf_thres:
                # Converti da cx,cy,w,h a x1,y1,x2,y2 (coordinate nel canvas 640x640)
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                
                x1 = int((cx - w/2) - pad_left) / scale
                y1 = int((cy - h/2) - pad_top) / scale
                x2 = int((cx + w/2) - pad_left) / scale
                y2 = int((cy + h/2) - pad_top) / scale
                
                boxes.append([x1, y1, x2, y2])
                scores.append(float(score))
                class_ids.append(int(class_id))
                
        # Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, scores, self.conf_thres, self.iou_thres)
        
        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                results.append({
                    "box": boxes[i], # [x1, y1, x2, y2]
                    "score": scores[i],
                    "class_id": class_ids[i]
                })
                
        return results, inference_time

    def draw_results(self, image, results):
        """
        Disegna i box sull'immagine originale.
        """
        img_copy = image.copy()
        for res in results:
            x1, y1, x2, y2 = map(int, res['box'])
            score = res['score']
            
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Nozzle: {score:.2f}"
            cv2.putText(img_copy, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
        return img_copy
