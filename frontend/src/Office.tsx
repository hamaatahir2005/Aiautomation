import {Suspense,useRef,useState} from 'react';
import {Canvas,useFrame,ThreeEvent} from '@react-three/fiber';
import {OrbitControls,Grid,ContactShadows,Float,Html} from '@react-three/drei';
import * as THREE from 'three';
export const departments=['AI Manager','Video Editor','Worldwide Lead Finder','Gmail Email Agent','Sales Agent','Marketing Agent','Customer Support','Finance Agent','Analytics Agent','Operations Agent'];
function Employee({position,index,active,onSelect}:{position:[number,number,number],index:number,active:boolean,onSelect:(name:string)=>void}){
 const ref=useRef<THREE.Group>(null);const [hover,setHover]=useState(false);
 useFrame(({clock})=>{if(ref.current)ref.current.position.y=.92+Math.sin(clock.elapsedTime*2+index)*.045;});
 const color=active?'#55f3c1':index%2?'#9477ff':'#48c9fa';
 return <group position={position} onClick={(e:ThreeEvent<MouseEvent>)=>{e.stopPropagation();onSelect(departments[index]);}} onPointerOver={()=>{setHover(true);document.body.style.cursor='pointer';}} onPointerOut={()=>{setHover(false);document.body.style.cursor='auto';}}>
  <mesh position={[0,.46,0]} castShadow><boxGeometry args={[1.55,.12,.95]}/><meshStandardMaterial color={hover?'#30465f':'#1a2b45'} metalness={.5} roughness={.35}/></mesh>
  {[-.62,.62].map(x=><mesh key={x} position={[x,.2,0]}><boxGeometry args={[.09,.4,.7]}/><meshStandardMaterial color="#22344d"/></mesh>)}
  <mesh position={[0,.88,-.25]}><boxGeometry args={[.88,.55,.065]}/><meshStandardMaterial color="#0c1728"/></mesh>
  <mesh position={[0,.88,-.208]}><planeGeometry args={[.78,.44]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={hover?1:.35}/></mesh>
  <mesh position={[0,.62,-.25]}><cylinderGeometry args={[.045,.08,.22]}/><meshStandardMaterial color="#516d85"/></mesh>
  <mesh position={[0,.55,.15]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[.52,.18]}/><meshStandardMaterial color="#344c69"/></mesh>
  <group ref={ref} position={[0,.92,.65]}>
   <mesh castShadow><capsuleGeometry args={[.15,.25,4,8]}/><meshStandardMaterial color={index%2?'#7c68df':'#238fae'} metalness={.4} roughness={.35}/></mesh>
   <mesh position={[0,.31,0]}><sphereGeometry args={[.18,16,16]}/><meshStandardMaterial color="#cedceb"/></mesh>
   <mesh position={[0,.32,-.145]}><boxGeometry args={[.23,.075,.07]}/><meshStandardMaterial color="#101b31" emissive={color} emissiveIntensity={.4}/></mesh>
  </group>
  <mesh position={[0,.015,0]} rotation={[-Math.PI/2,0,0]}><ringGeometry args={[.87,.9,48]}/><meshBasicMaterial color={color} transparent opacity={hover?.8:.15}/></mesh>
  <Html center position={[0,1.65,0]} distanceFactor={10}><button className={'office-label '+(active?'working':'')} onClick={()=>onSelect(departments[index])}><i/>{departments[index]}</button></Html>
 </group>;
}
export default function Office({active,onSelect}:{active:string[],onSelect:(name:string)=>void}){
 return <Canvas shadows camera={{position:[10,11,12],fov:40}} dpr={[1,1.75]}><color attach="background" args={['#0b1223']}/><fog attach="fog" args={['#0b1223',20,42]}/><ambientLight intensity={.8}/><directionalLight position={[3,12,5]} intensity={2} castShadow shadow-mapSize={[1024,1024]}/><pointLight position={[-4,3,-3]} color="#865cff" intensity={25}/><pointLight position={[5,3,2]} color="#29bfff" intensity={20}/><Suspense fallback={null}>
 <mesh receiveShadow position={[0,-.16,0]}><boxGeometry args={[14,.3,10]}/><meshStandardMaterial color="#111e33" metalness={.3} roughness={.6}/></mesh>
 <Grid position={[0,.005,0]} args={[14,10]} cellSize={.5} cellThickness={.3} cellColor="#263a55" sectionSize={2} sectionColor="#304c70" fadeDistance={30}/>
 <mesh position={[-6.7,.65,0]}><boxGeometry args={[.15,1.3,10]}/><meshStandardMaterial color="#1d3150" transparent opacity={.7}/></mesh>
 <mesh position={[0,.65,-4.7]}><boxGeometry args={[14,1.3,.15]}/><meshStandardMaterial color="#233857" transparent opacity={.7}/></mesh>
 {departments.map((_,i)=><Employee key={i} index={i} position={[(i%5-2)*2.5,0,(Math.floor(i/5)-.5)*3.8]} active={active.includes(departments[i])} onSelect={onSelect}/>)}
 <Float speed={1.4} floatIntensity={.25}><mesh position={[0,2.8,0]} rotation={[0,Math.PI/4,0]}><octahedronGeometry args={[.4]}/><meshStandardMaterial color="#6be9f4" emissive="#24a7bb" emissiveIntensity={.7} wireframe/></mesh></Float>
 <ContactShadows position={[0,-.01,0]} opacity={.3} scale={20} blur={2} far={5}/><OrbitControls makeDefault minDistance={8} maxDistance={24} minPolarAngle={.25} maxPolarAngle={Math.PI/2.2} target={[0,.2,0]}/></Suspense></Canvas>;
}
